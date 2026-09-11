"""
Build the search index from every PDF in data/pdfs.

Run from the project root:
    python -m backend.build_index
"""
from __future__ import annotations

from . import config
from .search.index import build_index


def main() -> None:
    print(f"Reading PDFs from: {config.PDF_DIR}")
    index = build_index()
    docs = index["documents"]
    if not docs:
        print("No PDFs found. Put medicine PDFs in data/pdfs and run again.")
        print("Tip: python -m backend.fetch_sample_pdfs")
        return
    print(f"Indexed {len(docs)} document(s), {len(index['chunks'])} chunks:")
    for d in docs.values():
        print(f"  - {d['drug_id']:12} {d['pages']:>4} pages  "
              f"{d['num_chunks']:>4} chunks  ({d['filename']})")
    print(f"Index written to: {config.INDEX_FILE}")


if __name__ == "__main__":
    main()
