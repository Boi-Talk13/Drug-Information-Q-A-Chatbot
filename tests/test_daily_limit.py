"""
Tests for the per-user daily question limit and the shared saved-answer cache.

    python3 -m tests.test_daily_limit

Runs the real /api/chat endpoint, but safely:
  * on a throw-away copy of the search index and a temporary SQLite database,
    so your real chat history and cache are never touched;
  * with the AI mocked out, so it spends ZERO Groq tokens;
  * with the limit lowered to 3, so it is quick to hit.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="medcite-limit-test-"))
shutil.copy(ROOT / "data" / "index" / "index.json", TMP / "index.json")

# Must be set BEFORE importing the backend (config reads env at import time).
os.environ["INDEX_FOLDER"] = str(TMP)
os.environ["DATABASE_URL"] = ""          # temporary SQLite in TMP, not Postgres
os.environ["DAILY_QUESTION_LIMIT"] = "3"
os.environ["PDF_FOLDER"] = str(ROOT / "data" / "pdfs")

from fastapi.testclient import TestClient  # noqa: E402

import backend.ai_answer.answer as answer_mod  # noqa: E402
from backend.api.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Mock AI: counts calls instead of calling Groq. A question containing
# "BACKUP" pretends Groq failed and the backup writer answered.
# ---------------------------------------------------------------------------
ai_calls: dict[str, int] = {}
_calls_lock = threading.Lock()


def fake_writer(query, hits, weak=False):
    with _calls_lock:
        ai_calls[query] = ai_calls.get(query, 0) + 1
    threading.Event().wait(0.05)  # overlap parallel requests in the race test
    if "backup" in query.lower():
        return f"Backup text [p. {hits[0].page}].", "extractive"
    return f"Mock AI answer [p. {hits[0].page}].", "llm"


answer_mod.write_answer_with_mode = fake_writer

passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    passed += ok
    failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def ask(client, user, question, drug="linzess", history=None):
    r = client.post("/api/chat", json={"question": question, "drug_filter": drug,
                                       "user_id": user, "history": history or []})
    assert r.status_code == 200, r.text
    return r.json()


def total_ai_calls() -> int:
    return sum(ai_calls.values())


with TestClient(app) as client:
    print("Daily limit = 3, AI mocked, temporary database\n")

    print("1. Each AI answer counts")
    for n, q in enumerate(["what is the recommended dose of linzess",
                           "can pregnant women take linzess safely",
                           "what are the side effects of linzess"], 1):
        res = ask(client, "user-A", q)
        check(f"question {n} answered, used={n}",
              not res.get("limit_reached") and res["usage"]["used"] == n, str(res.get("usage")))

    print("\n2. At the limit, a NEW question is stopped before the AI is called")
    before = total_ai_calls()
    res = ask(client, "user-A", "who should not take linzess at all")
    check("limit_reached is true", res.get("limit_reached") is True)
    check("the AI was not called", total_ai_calls() == before)
    check("remaining is 0", res["usage"]["remaining"] == 0, str(res["usage"]))
    check("message explains the limit (not 'no information')", "questions for today" in res["answer"])

    print("\n3. At the limit, a question asked BEFORE is answered from the database")
    before = total_ai_calls()
    res = ask(client, "user-A", "What is the recommended DOSE of Linzess?")  # same words, other case
    check("served from cache", res.get("from_cache") is True)
    check("the AI was not called", total_ai_calls() == before)
    check("not counted (still 3 used)", res["usage"]["used"] == 3, str(res["usage"]))

    print("\n4. Greetings and off-topic refusals are free and not blocked by the limit")
    res = ask(client, "user-A", "hi")
    check("greeting still works", not res.get("limit_reached") and not res.get("is_refusal"), str(res)[:120])
    res = ask(client, "user-A", "what is the capital of france")
    check("off-topic gets a normal refusal, not the limit message",
          res.get("is_refusal") and not res.get("limit_reached"))

    print("\n5. Another user asking the same question gets the saved answer free")
    before = total_ai_calls()
    res = ask(client, "user-B", "can pregnant women take linzess safely")
    check("served from cache for a different user", res.get("from_cache") is True)
    check("the AI was not called", total_ai_calls() == before)
    check("user-B has used 0", res["usage"]["used"] == 0, str(res["usage"]))

    print("\n6. A backup-writer answer does not count and is not saved")
    q = "linzess BACKUP storage temperature details"
    res = ask(client, "user-B", q)
    check("not counted", res["usage"]["used"] == 0, str(res["usage"]))
    before = total_ai_calls()
    res = ask(client, "user-B", q)
    check("asked again -> AI tried again (not served from cache)",
          total_ai_calls() == before + 1 and not res.get("from_cache"))

    print("\n7. A follow-up that depends on the chat is never served from the cache")
    hist = [{"role": "user", "text": "what is the recommended dose of linzess"},
            {"role": "assistant", "text": "290 mcg once daily [p. 2]."}]
    before = total_ai_calls()
    res = ask(client, "user-B", "what about for children then", history=hist)
    check("follow-up went to the AI", total_ai_calls() == before + 1 and not res.get("from_cache"))

    print("\n8. GET /api/usage reports the allowance")
    u = client.get("/api/usage", params={"user_id": "user-A"}).json()
    check("user-A: used 3, remaining 0", u == {"used": 3, "limit": 3, "remaining": 0}, str(u))

    print("\n9. Six questions at the SAME moment still stop at exactly 3")
    results = []
    questions = [f"what does the label say about linzess topic number {i}" for i in range(6)]
    threads = [threading.Thread(target=lambda q=q: results.append(ask(client, "user-C", q)))
               for q in questions]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    answered = sum(1 for r in results if not r.get("limit_reached"))
    stopped = sum(1 for r in results if r.get("limit_reached"))
    check("exactly 3 answered, 3 stopped", (answered, stopped) == (3, 3),
          f"answered={answered} stopped={stopped}")
    u = client.get("/api/usage", params={"user_id": "user-C"}).json()
    check("user-C used exactly 3", u["used"] == 3, str(u))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
