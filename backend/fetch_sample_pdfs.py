"""
Download the sample medicine PDFs into data/pdfs, then build the index.

These are the free, public prescribing-information PDFs the frontend already
lists. Run from the project root:

    python -m backend.fetch_sample_pdfs

The file names are chosen so their drug id matches the frontend
(rinvoq_pi.pdf -> "rinvoq", etc.), so the medicine dropdown lines up with the
indexed documents.
"""
from __future__ import annotations

import sys

import requests

from . import config
from .search.index import build_index

SAMPLES = {
    "rinvoq_pi.pdf": "https://www.rxabbvie.com/pdf/rinvoq_pi.pdf",
    "humira_pi.pdf": "https://www.rxabbvie.com/pdf/humira_pi.pdf",
    # Add more public labels here as needed.
}


def main() -> None:
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (MedCite sample fetcher)"}
    ok = 0
    for name, url in SAMPLES.items():
        dest = config.PDF_DIR / name
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"  already have {name}")
            ok += 1
            continue
        try:
            print(f"  downloading {name} ...", end=" ", flush=True)
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"{len(r.content)//1024} KB")
            ok += 1
        except Exception as e:  # pragma: no cover - network dependent
            print(f"failed ({e})")

    if ok:
        print("Building index ...")
        build_index()
        print("Done. Start the API with:  uvicorn backend.api.main:app --port 8000")
    else:
        print("No PDFs downloaded. Check your network or add PDFs manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
