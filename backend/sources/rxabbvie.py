"""Source verification: a PDF may only be added if it comes from RxAbbVie.

The medicine library is not open to arbitrary files. To add a PDF the user must
paste the official RxAbbVie link it came from, and we check three things before
the file is ever parsed:

  1. HOST   — the link is on rxabbvie.com (no other site, no look-alike host).
  2. CATALOG— the file it names is one of the PDFs actually published on
              https://www.rxabbvie.com/ (see rxabbvie_catalog.json).
  3. NAME   — the uploaded file's name matches the file the link names, so a
              link to one medicine cannot be used to smuggle in a different PDF.

The catalog is a snapshot of the site's PDF list; refresh it with
`python -m backend.sources.rxabbvie --refresh`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Set, Tuple
from urllib.parse import unquote, urlparse

_CATALOG_FILE = Path(__file__).with_name("rxabbvie_catalog.json")

# Only these hosts are accepted. Kept as an exact set rather than a suffix test
# so "rxabbvie.com.evil.example" and similar look-alikes cannot slip through.
ALLOWED_HOSTS = {"www.rxabbvie.com", "rxabbvie.com"}
ALLOWED_PATH_PREFIX = "/pdf/"


def _load_catalog() -> Set[str]:
    """Load the saved list of rxabbvie.com PDF filenames, lowercased."""
    try:
        data = json.loads(_CATALOG_FILE.read_text())
        return {n.lower() for n in data.get("filenames", [])}
    except Exception:
        return set()


CATALOG: Set[str] = _load_catalog()


def catalog_size() -> int:
    """Number of PDFs in the rxabbvie.com catalog snapshot."""
    return len(CATALOG)


def filename_from_url(url: str) -> Optional[str]:
    """The PDF file name a link points at, or None if it isn't a PDF link."""
    try:
        path = unquote(urlparse(url.strip()).path or "")
    except Exception:
        return None
    name = path.rsplit("/", 1)[-1].lower()
    return name if name.endswith(".pdf") else None


def _norm_name(name: str) -> str:
    """Compare names ignoring case and the browser's " (1)" copy suffix.

    A file downloaded twice lands as "rinvoq_pi (1).pdf"; that is still the same
    document, so it should not be rejected for a mismatch.
    """
    stem = Path(name).name.lower()
    stem = re.sub(r"\s*\(\d+\)(?=\.pdf$)", "", stem)
    return stem.strip()


def verify_source_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """Check a pasted link. Returns (ok, reason, catalog filename)."""
    url = (url or "").strip()
    if not url:
        return False, ("A source link is required. Paste the official RxAbbVie link "
                       "for this PDF, e.g. https://www.rxabbvie.com/pdf/rinvoq_pi.pdf"), None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "The source link must start with https://", None

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return False, (f'Only RxAbbVie links are accepted. "{host or url}" is not '
                       "rxabbvie.com, so this PDF cannot be added."), None

    if not parsed.path.lower().startswith(ALLOWED_PATH_PREFIX):
        return False, "An RxAbbVie PDF link looks like https://www.rxabbvie.com/pdf/<name>.pdf", None

    name = filename_from_url(url)
    if not name:
        return False, "The link must point directly at a .pdf file.", None

    if CATALOG and name not in CATALOG:
        return False, (f'"{name}" is not one of the {len(CATALOG)} PDFs published on '
                       "rxabbvie.com. Check the link from the RxAbbVie website."), None

    return True, "", name


def verify_upload(url: str, uploaded_filename: str) -> Tuple[bool, str, Optional[str]]:
    """Full gate: the link is a real RxAbbVie PDF AND the file matches it."""
    ok, reason, name = verify_source_url(url)
    if not ok:
        return False, reason, None

    if _norm_name(uploaded_filename) != _norm_name(name or ""):
        return False, (f'The file you chose ("{Path(uploaded_filename).name}") does not match '
                       f'the link, which points to "{name}". Upload the same PDF the link '
                       "refers to, or paste the link for the file you picked."), None

    return True, "", name


def _refresh() -> None:  # pragma: no cover - maintenance helper
    """Re-download the RxAbbVie index page and rewrite the catalog."""
    import urllib.request

    req = urllib.request.Request("https://www.rxabbvie.com/",
                                 headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    hrefs = re.findall(r'href="([^"]*\.pdf)"', html, re.I)
    names = sorted({h.rsplit("/", 1)[-1].lower() for h in hrefs})
    _CATALOG_FILE.write_text(json.dumps(
        {"host": "www.rxabbvie.com", "path_prefix": "/pdf/",
         "source": "https://www.rxabbvie.com/", "count": len(names),
         "filenames": names}, indent=1))
    print(f"catalog refreshed: {len(names)} PDFs")


if __name__ == "__main__":  # pragma: no cover
    import sys
    if "--refresh" in sys.argv:
        _refresh()
    else:
        print(f"{catalog_size()} RxAbbVie PDFs in catalog")
