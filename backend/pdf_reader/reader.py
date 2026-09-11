"""
Read a medicine PDF and keep the page number of every line.

This is the most important step in the whole project: if we lose the page
number here, we can never show a correct citation later. We use PyMuPDF, which
is the one PDF library that reliably keeps the page a piece of text came from.

Page numbers are 1-based *physical* pages, i.e. page 1 is the first page of the
file. That is exactly what the PDF viewer in the frontend navigates to, so the
citation the user clicks always lands on the page the text really lives on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


@dataclass
class PageText:
    """The cleaned text of a single physical PDF page."""
    page: int            # 1-based physical page number
    text: str            # normalised text of the page
    raw: str = ""        # original text, kept for exact-line lookup


@dataclass
class PdfDocument:
    drug_id: str
    filename: str
    title: str
    num_pages: int
    pages: List[PageText] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------
def _normalise(text: str) -> str:
    """Tidy PDF text without dropping the words that make citations work."""
    if not text:
        return ""
    # Join words split by a hyphen at a line break: "adminis-\ntration" -> "administration"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Turn single newlines into spaces (keep paragraph breaks as double newline).
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # Collapse runs of whitespace.
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def drug_id_from_filename(filename: str) -> str:
    """`rinvoq_pi.pdf` -> `rinvoq`, `Humira PI.PDF` -> `humira`.

    The frontend identifies each drug by a short id (rinvoq, humira, ...). We
    derive the same id from the file name so `drug_filter` from the UI lines up
    with the indexed documents. We strip a trailing `_pi` / `-pi` (prescribing
    information) marker that the sample files use.
    """
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[\s\-]+", "_", stem)
    stem = re.sub(r"_(pi|prescribing_information|prescribing_info|label)$", "", stem)
    stem = re.sub(r"[^a-z0-9_]", "", stem)
    return stem or "document"


def _title_from_first_page(text: str, fallback: str) -> str:
    """Best-effort human title from the first non-empty line of the PDF."""
    for line in text.splitlines():
        line = line.strip()
        # Skip boilerplate lines like "HIGHLIGHTS OF PRESCRIBING INFORMATION".
        if len(line) < 3:
            continue
        if "HIGHLIGHTS" in line.upper():
            continue
        return line[:120]
    return fallback


def read_pdf(path: str | Path) -> PdfDocument:
    """Extract every page of a PDF, keeping the physical page number."""
    path = Path(path)
    filename = path.name
    drug_id = drug_id_from_filename(filename)

    pages: List[PageText] = []
    with fitz.open(path) as doc:
        num_pages = doc.page_count
        for i in range(num_pages):
            raw = doc.load_page(i).get_text("text") or ""
            pages.append(PageText(page=i + 1, text=_normalise(raw), raw=raw))

    first = pages[0].text if pages else ""
    title = _title_from_first_page(first, fallback=drug_id.upper())

    return PdfDocument(
        drug_id=drug_id,
        filename=filename,
        title=title,
        num_pages=len(pages),
        pages=pages,
    )
