"""
A small record of every question and answer, for monitoring.

The design calls for keeping a record of every answer (how many questions, how
many refusals, how fast, how many errors) and shows the refusal count proudly.
We use SQLite so it works with zero setup on a laptop and in one container. In
production this is the piece you swap for PostgreSQL; the shape is the same.

Logging never breaks a request: any failure here is swallowed.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional

from .. import config

_DB_PATH = config.INDEX_DIR / "medcite_log.db"
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                question TEXT,
                drug TEXT,
                is_refusal INTEGER,
                is_advice INTEGER,
                num_citations INTEGER,
                pages TEXT,
                latency_ms INTEGER,
                mode TEXT
            )
            """
        )
        _conn.commit()
    return _conn


def log_answer(question: str, drug: Optional[str], result: Dict, latency_ms: int) -> None:
    try:
        conn = _connect()
        pages = ",".join(str(c.get("page")) for c in result.get("citations", []))
        conn.execute(
            "INSERT INTO answers (ts, question, drug, is_refusal, is_advice, "
            "num_citations, pages, latency_ms, mode) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                time.time(),
                question[:500],
                drug,
                1 if result.get("is_refusal") else 0,
                1 if result.get("is_advice") else 0,
                len(result.get("citations", [])),
                pages,
                latency_ms,
                "groq" if config.USE_LLM else "extractive",
            ),
        )
        conn.commit()
    except Exception:
        pass


def stats() -> Dict:
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT COUNT(*), "
            "SUM(is_refusal), SUM(is_advice), "
            "AVG(latency_ms) FROM answers"
        ).fetchone()
        total = row[0] or 0
        refusals = row[1] or 0
        advice = row[2] or 0
        avg_latency = int(row[3]) if row[3] else 0
        return {
            "total_questions": total,
            "refusals": refusals,
            "refusal_rate": round(refusals / total, 3) if total else 0.0,
            "advice_answers": advice,
            "avg_latency_ms": avg_latency,
        }
    except Exception:
        return {"total_questions": 0, "refusals": 0, "refusal_rate": 0.0,
                "advice_answers": 0, "avg_latency_ms": 0}
