"""
Score MedCite against a labeled question set in tests/.

    python3 -m tests.evaluate                              # tests/questions.json
    python3 -m tests.evaluate --file holdout.json          # another set
    python3 -m tests.evaluate --file tough.json --resume   # continue a stopped run
    python3 -m tests.evaluate --delay 4                    # slower, if Groq rate-limits
    python3 -m tests.evaluate --only lin                   # just ids starting "lin"

MedCite is not a trained classifier, so there is no single built-in "F1 score".
F1 needs a yes/no decision checked against a known right answer. This script
measures the two decisions MedCite actually makes:

  1. REFUSAL F1   — did it refuse exactly the questions it should refuse?
                    (positive class = "refuse"; a classic binary F1)
  2. CITATION F1  — does it cite the place where the answer really is?
                    precision = cited pages that are correct / all cited pages
                    recall    = answerable questions where at least one cited
                                page is inside the right section
                    gold_pages lists every page the answering section covers,
                    i.e. the ACCEPTABLE pages. A correct answer about a
                    3-page dosage section cites one of them, not all three, so
                    requiring every page would cap recall for right answers.
                    That stricter number is still printed, for reference.

It calls answer_question() directly, so nothing is written to the database or
the answer cache — running it does not pollute chat_history.

AI-only results. If the AI stops answering mid-run (most often the Groq free
tier's daily token limit), MedCite silently switches to its backup extractive
writer. The run STOPS at that point, because the scores would describe the
backup rather than the AI. Pass --allow-fallback to score the backup on purpose.

Saved progress. Every answer is written to tests/results/<set>.json as soon as
it arrives, so tokens already spent are never lost. After a stop, run again
with --resume to continue from the first unanswered question. Without --resume
the selected questions are re-asked from scratch (other saved rows are kept).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from backend import config
from backend.ai_answer.answer import answer_question
from backend.search.hybrid import Retriever

TESTS = Path(__file__).parent
RESULTS = TESTS / "results"


def f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if (p + r) else 0.0


def _results_path(set_file: str) -> Path:
    return RESULTS / f"{Path(set_file).stem}.json"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _save(path: Path, meta: dict, rows: dict) -> None:
    # Write to a temp file then swap, so a crash mid-write never corrupts the
    # answers already saved.
    RESULTS.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({**meta, "rows": rows}, indent=1))
    tmp.replace(path)


def _passed(row: dict) -> bool:
    should_refuse = row["expect"] == "refuse"
    if row["refused"] != should_refuse:
        return False
    return should_refuse or bool(set(row["cited"]) & set(row["gold"]))


def _print_row(n: int, total: int, qid: str, row: dict) -> None:
    hit = ""
    if row["expect"] == "answer":
        hit = f"{len(set(row['cited']) & set(row['gold']))}/{len(row['cited'])} cited ok"
    backup = "  (backup writer)" if row.get("mode") == "extractive" else ""
    print(f"[{n:2d}/{total}] {'PASS' if _passed(row) else 'FAIL'}  {qid:14} "
          f"expect={row['expect']:6} got={'refuse' if row['refused'] else 'answer':6} "
          f"cited={row['cited']!s:14} gold={row['gold']!s:14} {hit:14} {row['secs']:4.1f}s{backup}")


def summarize(items: list, rows: dict, meta: dict) -> None:
    tp = fp = fn = tn = 0                       # refusal, positive class = refuse
    cite_correct = cite_total = gold_total = 0  # page-level citation counts
    answerable = located = fallbacks = 0

    for q in items:
        row = rows[q["id"]]
        should_refuse = row["expect"] == "refuse"
        refused = row["refused"]
        if should_refuse and refused:
            tp += 1
        elif not should_refuse and refused:
            fp += 1
        elif should_refuse and not refused:
            fn += 1
        else:
            tn += 1
        fallbacks += row.get("mode") == "extractive"
        if not should_refuse:
            cited, gold = set(row["cited"]), set(row["gold"])
            cite_correct += len(cited & gold)
            cite_total += len(cited)
            gold_total += len(gold)
            answerable += 1
            located += bool(cited & gold)

    r_prec = tp / (tp + fp) if (tp + fp) else 0.0
    r_rec = tp / (tp + fn) if (tp + fn) else 0.0
    c_prec = cite_correct / cite_total if cite_total else 0.0
    c_rec = located / answerable if answerable else 0.0
    strict_rec = cite_correct / gold_total if gold_total else 0.0
    passed = sum(_passed(rows[q["id"]]) for q in items)

    print("\n" + "=" * 62)
    print(f"SET {meta['set']}   model {meta['model']}   top_k {meta['top_k']}")
    print()
    print("REFUSAL DETECTION   (positive class = should refuse)")
    print(f"   confusion matrix     TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"   precision {r_prec:.3f}   recall {r_rec:.3f}   F1 {f1(r_prec, r_rec):.3f}")
    print(f"   accuracy  {(tp + tn) / len(items):.3f}")
    print()
    print("CITATIONS           (answerable questions)")
    print(f"   precision {c_prec:.3f}   ({cite_correct} of {cite_total} cited pages were in the right section)")
    print(f"   recall    {c_rec:.3f}   ({located} of {answerable} answers cited the right section)")
    print(f"   F1        {f1(c_prec, c_rec):.3f}")
    print(f"   reference: strict page recall {strict_rec:.3f} "
          f"(every page of every section, {cite_correct}/{gold_total}) — "
          f"F1 on that basis {f1(c_prec, strict_rec):.3f}")
    print()
    if fallbacks:
        print(f"WARNING             {fallbacks} answer(s) came from the BACKUP writer, not the AI.")
        print("                    Citation scores above do not describe the AI.")
        print()
    print(f"OVERALL             {passed}/{len(items)} questions passed")
    failed = [q["id"] for q in items if not _passed(rows[q["id"]])]
    if failed:
        print(f"   failed: {', '.join(failed)}")
    print("=" * 62)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="questions.json",
                    help="question set in tests/ (e.g. holdout.json)")
    ap.add_argument("--resume", action="store_true",
                    help="keep saved answers and only ask the questions not answered yet")
    ap.add_argument("--delay", type=float, default=2.5,
                    help="seconds between questions (avoids Groq rate limits)")
    ap.add_argument("--only", default="", help="only run ids starting with this")
    ap.add_argument("--allow-fallback", action="store_true",
                    help="keep going if the AI is unavailable and the backup writer answers")
    args = ap.parse_args()

    items = [q for q in json.loads((TESTS / args.file).read_text())["questions"]
             if q["id"].startswith(args.only)]
    if not items:
        raise SystemExit(f"No questions to run — check tests/{args.file} or --only.")

    path = _results_path(args.file)
    meta = {"set": args.file, "model": config.AI_MODEL, "top_k": config.TOP_K}
    rows = _load(path).get("rows", {})
    selected = {q["id"] for q in items}
    if not args.resume:
        rows = {k: v for k, v in rows.items() if k not in selected}
    if not args.allow_fallback:
        # A backup-writer answer never counts as done in an AI-only run.
        rows = {k: v for k, v in rows.items() if v.get("mode") != "extractive"}
    # Saved rows keep what MedCite answered, but always score them against the
    # CURRENT answer key: keys are rebuilt from the PDFs (build_answer_keys.py),
    # and a stale key saved with an old run would mark right answers wrong.
    for q in items:
        if q["id"] in rows:
            rows[q["id"]]["expect"] = q["expect"]
            rows[q["id"]]["gold"] = sorted(q["gold_pages"])

    todo = [q for q in items if q["id"] not in rows]
    done_before = len(items) - len(todo)
    resumed = f", {done_before} already saved" if done_before else ""
    print(f"Running {len(todo)} of {len(items)} questions{resumed} (delay {args.delay}s)...\n")

    retriever = Retriever()
    for n, q in enumerate(todo, 1):
        started = time.perf_counter()
        result = answer_question(question=q["question"], history=[],
                                 drug_filter=q["drug"], retriever=retriever,
                                 user_id="shared")
        secs = time.perf_counter() - started

        mode = result.get("answer_mode")
        if mode == "extractive" and not args.allow_fallback:
            _save(path, meta, rows)
            saved = len(selected & rows.keys())
            raise SystemExit(
                f"\nSTOPPED at {q['id']}: the AI did not write this answer, the backup "
                "extractive writer did. This is usually the Groq daily token limit — see the "
                "[llm] line above for the exact reason.\n"
                f"{saved} of {len(items)} answers are saved in "
                f"{path.relative_to(TESTS.parent)}. When the limit refills, continue with:\n"
                f"    python3 -m tests.evaluate --file {args.file} --resume")

        row = {
            "expect": q["expect"],
            "refused": bool(result.get("is_refusal")),
            "cited": sorted({c.get("page") for c in result.get("citations", []) if c.get("page")}),
            "gold": sorted(q["gold_pages"]),
            "mode": mode,
            "secs": round(secs, 1),
            "at": time.strftime("%Y-%m-%d %H:%M"),
        }
        rows[q["id"]] = row
        meta["updated"] = row["at"]
        _save(path, meta, rows)
        _print_row(done_before + n, len(items), q["id"], row)
        if n < len(todo):
            time.sleep(args.delay)

    summarize(items, rows, meta)


if __name__ == "__main__":
    main()
