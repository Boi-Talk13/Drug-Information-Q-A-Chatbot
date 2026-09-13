"""
Rebuild the answer keys (gold_pages) of the labeled question sets from the PDFs.

    python3 -m tests.build_answer_keys           # rewrite gold_pages in all sets
    python3 -m tests.build_answer_keys --check   # only show what would change

Why this exists: the keys used to be copied from the search index's page
numbers, and an earlier text splitter labelled about 1 piece in 4 with the
wrong page. A key built that way marks correct answers as wrong. So each
question now says WHAT it is about, and this script finds the pages:

  gold_sections  — a question about a label section ("what is the dose?").
                   Key = every page that section covers, from the section
                   headings in the search index (page numbers 99.8% correct).
  gold_text      — a question about one specific fact ("can I crush K-TAB?").
                   Key = every PDF page whose real text matches the fact,
                   read straight from the PDF with PyMuPDF.

Neither ever looks at MedCite's answers, so the tests cannot be tuned to pass.
Build the index first (python -m backend.build_index), then run this.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

from backend import config

TESTS = Path(__file__).parent
SETS = ["questions.json", "holdout.json", "tough.json"]


def _pdf_page_texts(filename: str) -> list[str]:
    """Each page's text, with words broken across lines joined back together."""
    doc = fitz.open(config.PDF_DIR / config.SHARED_OWNER / filename)
    texts = []
    for page in doc:
        t = page.get_text()
        t = re.sub(r"-\n(?=[a-z])", "", t)   # "hyper-\nkalemia" -> "hyperkalemia"
        texts.append(re.sub(r"\s+", " ", t))
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report changes without writing")
    args = ap.parse_args()

    index = json.loads(config.INDEX_FILE.read_text())
    shared = {d["drug_id"]: d for d in index["documents"].values()
              if d.get("owner") == config.SHARED_OWNER}
    page_texts: dict[str, list[str]] = {}
    problems = 0

    for set_file in SETS:
        path = TESTS / set_file
        data = json.loads(path.read_text())
        changed = 0
        print(f"== {set_file}")
        for q in data["questions"]:
            if q["expect"] != "answer":
                continue
            drug = q["drug"]
            if "gold_sections" in q:
                prefixes = [p.upper() for p in q["gold_sections"]]
                pages = sorted({p for c in index["chunks"]
                                if c["drug_id"] == drug and c.get("owner") == config.SHARED_OWNER
                                and c["section"].upper().startswith(tuple(prefixes))
                                for p in c.get("pages", [c["page"]])})
                how = "section"
            elif "gold_text" in q:
                if drug not in page_texts:
                    page_texts[drug] = _pdf_page_texts(shared[drug]["filename"])
                pattern = re.compile(q["gold_text"], re.I)
                pages = [i + 1 for i, t in enumerate(page_texts[drug]) if pattern.search(t)]
                how = "text"
            else:
                print(f"   !! {q['id']}: has neither gold_sections nor gold_text")
                problems += 1
                continue

            if not pages:
                print(f"   !! {q['id']}: its {how} key matches NO page — fix the key")
                problems += 1
                continue
            if pages != q.get("gold_pages"):
                changed += 1
                print(f"   {q['id']:15} {how:7} {q.get('gold_pages')} -> {pages}")
                q["gold_pages"] = pages
        print(f"   {changed} key(s) changed")
        if not args.check:
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

    if problems:
        raise SystemExit(f"\n{problems} problem(s) — nothing is reliable until they are fixed.")


if __name__ == "__main__":
    main()
