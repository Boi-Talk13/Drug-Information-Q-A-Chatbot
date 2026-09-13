"""
Database layer for MedCite.

Primary store is **PostgreSQL** (as in the design doc). If DATABASE_URL is not
set or Postgres can't be reached, it automatically falls back to a local
**SQLite** file so the app never breaks in a demo.

Every per-user row carries a `user_id`, and every read is filtered by it — that
is how one user's chats and logs stay separate from another's. The shared
knowledge base (the PDF index) is not stored here; it is read-only for everyone.

A single module-level lock guards the shared connection, because FastAPI runs
sync endpoints on multiple threads and neither driver's connection is safe to
share across threads without it.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from .. import config

DATABASE_URL = config.DATABASE_URL

_conn = None
_backend = None          # "postgres" | "sqlite"
_lock = threading.Lock()


def _want_postgres() -> bool:
    if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
        return False
    try:
        import psycopg2  # noqa: F401
        return True
    except Exception:
        return False


def _connect():
    global _conn, _backend
    if _conn is not None:
        return _conn

    if _want_postgres():
        try:
            import psycopg2
            _conn = psycopg2.connect(DATABASE_URL)
            _conn.autocommit = True
            _backend = "postgres"
        except Exception as e:
            print(f"[db] Postgres unavailable ({e}); falling back to SQLite.")
            _conn = None

    if _conn is None:
        config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(config.INDEX_DIR / "medcite_log.db"), check_same_thread=False)
        _backend = "sqlite"

    _init_schema()
    return _conn


def backend_name() -> str:
    _connect()
    return _backend or "sqlite"


def _q(sql: str) -> str:
    """Translate '?' placeholders to '%s' for Postgres."""
    return sql.replace("?", "%s") if _backend == "postgres" else sql


def _init_schema() -> None:
    cur = _conn.cursor()
    if _backend == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id SERIAL PRIMARY KEY,
                ts DOUBLE PRECISION,
                user_id TEXT,
                question TEXT,
                drug TEXT,
                is_refusal INTEGER,
                is_advice INTEGER,
                num_citations INTEGER,
                pages TEXT,
                latency_ms INTEGER,
                mode TEXT
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                ts DOUBLE PRECISION,
                user_id TEXT,
                drug TEXT,
                question TEXT,
                answer TEXT,
                citations TEXT,
                is_refusal INTEGER
            )""")
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, user_id TEXT, question TEXT, drug TEXT,
                is_refusal INTEGER, is_advice INTEGER, num_citations INTEGER,
                pages TEXT, latency_ms INTEGER, mode TEXT
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, user_id TEXT, drug TEXT, question TEXT,
                answer TEXT, citations TEXT, is_refusal INTEGER
            )""")
    # answer_cache: same question (per user + drug) -> same saved answer.
    if _backend == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answer_cache (
                user_id TEXT, drug TEXT, qnorm TEXT, result TEXT, ts DOUBLE PRECISION,
                PRIMARY KEY (user_id, drug, qnorm)
            )""")
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answer_cache (
                user_id TEXT, drug TEXT, qnorm TEXT, result TEXT, ts REAL,
                PRIMARY KEY (user_id, drug, qnorm)
            )""")
    # daily_usage: AI-written answers each user got per day (the daily limit).
    # Same SQL on both databases.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_usage (
            user_id TEXT, day TEXT, ai_answers INTEGER,
            PRIMARY KEY (user_id, day)
        )""")
    # users: maps a browser token -> a short, sequential id (user-101, 102, ...)
    if _backend == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                seq SERIAL PRIMARY KEY,
                token TEXT UNIQUE,
                user_id TEXT,
                created_at DOUBLE PRECISION
            )""")
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE,
                user_id TEXT,
                created_at REAL
            )""")
        # Older SQLite files may predate user_id — add it if missing.
        try:
            cols = [r[1] for r in cur.execute("PRAGMA table_info(answers)").fetchall()]
            if "user_id" not in cols:
                cur.execute("ALTER TABLE answers ADD COLUMN user_id TEXT")
        except Exception:
            pass
    # index for fast per-user lookups
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON chat_history (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_answers_user ON answers (user_id)")
    except Exception:
        pass
    _conn.commit() if _backend == "sqlite" else None


# ---------------------------------------------------------------------------
# Users — map a per-browser token to a short sequential id (user-101, 102, ...)
# ---------------------------------------------------------------------------
def resolve_user(token: str) -> str:
    """Return the short id for this browser token, assigning the next number
    (user-101, user-102, ...) the first time we see it."""
    if not token:
        return "user-000"
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            cur.execute(_q("SELECT user_id FROM users WHERE token = ?"), (token,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            # Insert new; seq auto-increments, short id = user-(100+seq).
            if _backend == "postgres":
                cur.execute(_q("INSERT INTO users (token, created_at) VALUES (?, ?) "
                               "ON CONFLICT (token) DO NOTHING"), (token, time.time()))
            else:
                cur.execute(_q("INSERT OR IGNORE INTO users (token, created_at) VALUES (?, ?)"),
                            (token, time.time()))
                conn.commit()
            cur.execute(_q("SELECT seq FROM users WHERE token = ?"), (token,))
            seq = cur.fetchone()[0]
            short = f"user-{100 + int(seq)}"
            cur.execute(_q("UPDATE users SET user_id = ? WHERE token = ?"), (short, token))
            if _backend == "sqlite":
                conn.commit()
            return short
    except Exception as e:
        print(f"[db] resolve_user failed: {e}")
        return "user-000"


# ---------------------------------------------------------------------------
# Answer cache — same question, same answer (and instant, no Groq call)
# ---------------------------------------------------------------------------
def _index_sig() -> str:
    """A short fingerprint of the current search index.

    It is part of every cache key, so rebuilding the index (new PDFs, changed
    chunking) automatically misses the old entries instead of serving an answer
    that the current index would no longer produce.
    """
    try:
        from .. import config
        st = config.INDEX_FILE.stat()
        return f"{int(st.st_mtime)}-{st.st_size}"
    except Exception:
        return "0"


def _qnorm(q: str) -> str:
    # Lowercase, strip punctuation, then apply the same typo dictionary the
    # search layer uses. This means "pregent women..." and "pregnant women..."
    # hit the same cache key — one good answer is reused for typo variants.
    # The index fingerprint is prefixed so a rebuild invalidates stale answers.
    from ..search.spellfix import COMMON_FIXES
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", (q or "").lower())
    words = [COMMON_FIXES.get(w, w) for w in cleaned.split()]
    return f"{_index_sig()}|" + " ".join(words).strip()


def get_cached_answer(user_id: str, drug: Optional[str], question: str) -> Optional[Dict]:
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            cur.execute(_q("SELECT result FROM answer_cache WHERE user_id=? AND drug=? AND qnorm=?"),
                        (user_id, drug or "", _qnorm(question)))
            row = cur.fetchone()
        return json.loads(row[0]) if row and row[0] else None
    except Exception as e:
        print(f"[db] get_cached_answer failed: {e}")
        return None


def cache_answer(user_id: str, drug: Optional[str], question: str, result: Dict) -> None:
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            blob = json.dumps(result)
            if _backend == "postgres":
                cur.execute(_q(
                    "INSERT INTO answer_cache (user_id, drug, qnorm, result, ts) VALUES (?,?,?,?,?) "
                    "ON CONFLICT (user_id, drug, qnorm) DO UPDATE SET result=EXCLUDED.result, ts=EXCLUDED.ts"),
                    (user_id, drug or "", _qnorm(question), blob, time.time()))
            else:
                cur.execute(_q(
                    "INSERT OR REPLACE INTO answer_cache (user_id, drug, qnorm, result, ts) VALUES (?,?,?,?,?)"),
                    (user_id, drug or "", _qnorm(question), blob, time.time()))
                conn.commit()
    except Exception as e:
        print(f"[db] cache_answer failed: {e}")


# ---------------------------------------------------------------------------
# Per-user daily limit — only answers the AI actually writes are counted
# ---------------------------------------------------------------------------
def _today() -> str:
    """Today's date in USAGE_TIMEZONE, so the limit resets at local midnight
    (a server on UTC would otherwise reset it at 5:30 AM in India)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(config.USAGE_TIMEZONE)).strftime("%Y-%m-%d")
    except Exception:
        return time.strftime("%Y-%m-%d")


def usage_today(user_id: str) -> int:
    """How many AI-written answers this user has had today."""
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            cur.execute(_q("SELECT ai_answers FROM daily_usage WHERE user_id=? AND day=?"),
                        (user_id, _today()))
            row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception as e:
        print(f"[db] usage_today failed: {e}")
        return 0


def reserve_ai_answer(user_id: str, limit: int) -> bool:
    """Take one of today's AI answers for this user, if any are left.

    Reserving BEFORE the AI call — and releasing it afterwards if the AI was
    not used — keeps the limit exact even when one user sends several
    questions at once, because the check and the increment happen together
    under the lock.
    """
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            day = _today()
            cur.execute(_q("SELECT ai_answers FROM daily_usage WHERE user_id=? AND day=?"),
                        (user_id, day))
            row = cur.fetchone()
            if row and int(row[0]) >= limit:
                return False
            if row:
                cur.execute(_q("UPDATE daily_usage SET ai_answers = ai_answers + 1 "
                               "WHERE user_id=? AND day=?"), (user_id, day))
            else:
                cur.execute(_q("INSERT INTO daily_usage (user_id, day, ai_answers) VALUES (?,?,1)"),
                            (user_id, day))
            if _backend == "sqlite":
                conn.commit()
            return True
    except Exception as e:
        # A broken counter must never lock everyone out of the app.
        print(f"[db] reserve_ai_answer failed: {e}")
        return True


def release_ai_answer(user_id: str) -> None:
    """Give back a reserved answer that ended up not using the AI
    (a greeting, a refusal, or the backup writer)."""
    try:
        with _lock:
            conn = _connect()
            conn.cursor().execute(_q(
                "UPDATE daily_usage SET ai_answers = ai_answers - 1 "
                "WHERE user_id=? AND day=? AND ai_answers > 0"), (user_id, _today()))
            if _backend == "sqlite":
                conn.commit()
    except Exception as e:
        print(f"[db] release_ai_answer failed: {e}")


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def log_answer(question: str, drug: Optional[str], result: Dict,
               latency_ms: int, user_id: Optional[str] = None) -> None:
    try:
        with _lock:
            conn = _connect()
            pages = ",".join(str(c.get("page")) for c in result.get("citations", []))
            conn.cursor().execute(_q(
                "INSERT INTO answers (ts, user_id, question, drug, is_refusal, is_advice, "
                "num_citations, pages, latency_ms, mode) VALUES (?,?,?,?,?,?,?,?,?,?)"),
                (time.time(), user_id, question[:500], drug,
                 1 if result.get("is_refusal") else 0,
                 1 if result.get("is_advice") else 0,
                 len(result.get("citations", [])), pages, latency_ms,
                 "groq" if config.USE_LLM else "extractive"))
            if _backend == "sqlite":
                conn.commit()
    except Exception as e:
        print(f"[db] log_answer failed: {e}")


def save_chat(user_id: str, drug: Optional[str], question: str, result: Dict) -> None:
    try:
        with _lock:
            conn = _connect()
            conn.cursor().execute(_q(
                "INSERT INTO chat_history (ts, user_id, drug, question, answer, citations, is_refusal) "
                "VALUES (?,?,?,?,?,?,?)"),
                (time.time(), user_id, drug, question[:1000],
                 result.get("answer", "")[:4000],
                 json.dumps(result.get("citations", []))[:4000],
                 1 if result.get("is_refusal") else 0))
            if _backend == "sqlite":
                conn.commit()
    except Exception as e:
        print(f"[db] save_chat failed: {e}")


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def get_history(user_id: str, limit: int = 50) -> List[Dict]:
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            cur.execute(_q(
                "SELECT ts, drug, question, answer, citations, is_refusal FROM chat_history "
                "WHERE user_id = ? ORDER BY ts DESC LIMIT ?"),
                (user_id, limit))
            rows = cur.fetchall()
        out = []
        for ts, drug, q, a, cites, ref in rows:
            out.append({
                "ts": ts, "drug": drug, "question": q, "answer": a,
                "citations": json.loads(cites) if cites else [],
                "is_refusal": bool(ref),
            })
        return out
    except Exception as e:
        print(f"[db] get_history failed: {e}")
        return []


def get_history_by_day(user_id: str, limit: int = 100) -> List[Dict]:
    """Same history, but grouped into Today / Yesterday / older dates."""
    import datetime as _dt
    rows = get_history(user_id, limit)
    today = _dt.date.today()
    groups: Dict[str, List[Dict]] = {}
    order: List[str] = []
    for r in rows:
        d = _dt.date.fromtimestamp(r["ts"]) if r.get("ts") else today
        if d == today:
            label = "Today"
        elif d == today - _dt.timedelta(days=1):
            label = "Yesterday"
        else:
            label = d.strftime("%d %b %Y")
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append({"question": r["question"], "answer": r["answer"]})
    return [{"day": lbl, "count": len(groups[lbl]), "items": groups[lbl]} for lbl in order]


def stats(user_id: Optional[str] = None) -> Dict:
    try:
        with _lock:
            conn = _connect()
            cur = conn.cursor()
            if user_id:
                cur.execute(_q("SELECT COUNT(*), SUM(is_refusal), SUM(is_advice), AVG(latency_ms) "
                               "FROM answers WHERE user_id = ?"), (user_id,))
            else:
                cur.execute("SELECT COUNT(*), SUM(is_refusal), SUM(is_advice), AVG(latency_ms) FROM answers")
            row = cur.fetchone()
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM answers")
            users = cur.fetchone()[0] or 0
        total = row[0] or 0
        refusals = row[1] or 0
        return {
            "backend": _backend,
            "total_questions": total,
            "unique_users": users,
            "refusals": refusals,
            "refusal_rate": round(refusals / total, 3) if total else 0.0,
            "advice_answers": row[2] or 0,
            "avg_latency_ms": int(row[3]) if row[3] else 0,
        }
    except Exception as e:
        print(f"[db] stats failed: {e}")
        return {"backend": _backend, "total_questions": 0, "unique_users": 0,
                "refusals": 0, "refusal_rate": 0.0, "advice_answers": 0, "avg_latency_ms": 0}
