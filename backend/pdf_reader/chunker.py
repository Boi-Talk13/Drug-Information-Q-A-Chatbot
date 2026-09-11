"""
Cut a PDF into small pieces at the section headings, keeping the page number.

Why by section and not by size: if you cut every N letters, a dose can get cut
in half, and half a dose is worse than no dose. Drug labels have a clear
numbered structure (1 INDICATIONS, 2 DOSAGE, 5 WARNINGS, 6 ADVERSE REACTIONS,
8.4 Pediatric Use, BOXED WARNING, ...), so we split on those headings.

Every chunk carries:
  - page:  the physical page its text starts on (what the citation points to)
  - pages: every page the chunk spans (for verification)
  - section: the nearest heading above the text
The page a chunk reports is always a real page the text is on, so the citation
and the PDF viewer can never disagree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .reader import PdfDocument

# A section heading in an FDA label, e.g.
#   "1 INDICATIONS AND USAGE", "2.1 Recommended Dosage",
#   "5 WARNINGS AND PRECAUTIONS", "8.4 Pediatric Use"
_NUM_HEADING = re.compile(
    r"^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\s+([A-Z][A-Za-z].{2,80})$"
)
# Named headings without a number, e.g. "BOXED WARNING", "CONTRAINDICATIONS".
_NAMED_HEADING = re.compile(
    r"^\s*(BOXED WARNING[S]?|WARNING[S]?|CONTRAINDICATION[S]?|"
    r"INDICATIONS AND USAGE|DOSAGE AND ADMINISTRATION|ADVERSE REACTIONS|"
    r"DRUG INTERACTIONS|USE IN SPECIFIC POPULATIONS|OVERDOSAGE|"
    r"HOW SUPPLIED|DESCRIPTION|CLINICAL PHARMACOLOGY|"
    r"PATIENT COUNSELING INFORMATION)\s*[:.]?\s*$",
    re.IGNORECASE,
)

MAX_CHARS = 1100          # a piece is about half a page
OVERLAP_CHARS = 120       # small overlap so a fact on a boundary is not lost
MIN_CHUNK_CHARS = 40      # ignore tiny scraps


@dataclass
class Chunk:
    id: str
    drug_id: str
    filename: str
    section: str
    page: int                     # citation page (where the chunk starts)
    pages: List[int] = field(default_factory=list)
    text: str = ""


def _detect_heading(line: str) -> str | None:
    line = line.strip()
    if not line or len(line) > 90:
        return None
    m = _NUM_HEADING.match(line)
    if m:
        return f"{m.group(1)} {m.group(2).strip()}"
    m = _NAMED_HEADING.match(line)
    if m:
        return line.strip(" :.").upper()
    return None


def _flatten_lines(doc: PdfDocument):
    """Yield (page, line) for every visual line in reading order.

    We use the *raw* page text (before newline-collapsing) because heading
    detection depends on real line breaks — "1 INDICATIONS AND USAGE" must be
    its own line to be recognised as a heading.
    """
    for pg in doc.pages:
        source = pg.raw if pg.raw else pg.text
        for line in source.split("\n"):
            line = line.strip()
            if line:
                yield pg.page, line


def _split_long(text: str) -> List[str]:
    """Split an over-long section into overlapping windows at sentence bounds."""
    if len(text) <= MAX_CHARS:
        return [text]
    parts, start = [], 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            # Prefer to break at a sentence end inside the window.
            dot = text.rfind(". ", start + MAX_CHARS // 2, end)
            if dot != -1:
                end = dot + 1
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return [p for p in parts if p]


def chunk_document(doc: PdfDocument) -> List[Chunk]:
    """Turn a read PDF into section-aware chunks with page provenance."""
    chunks: List[Chunk] = []
    current_section = "PRESCRIBING INFORMATION"
    # buffer holds (page, line) for the current section.
    buffer: List[tuple[int, str]] = []

    def flush():
        nonlocal buffer
        if not buffer:
            return
        section_pages = [p for p, _ in buffer]
        body = " ".join(line for _, line in buffer).strip()
        body = re.sub(r"\s+", " ", body)
        if len(body) < MIN_CHUNK_CHARS:
            buffer = []
            return
        for piece in _split_long(body):
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            # The page a piece belongs to = the page of the first line that
            # falls inside it. We approximate by mapping character offset back
            # to the line/page sequence.
            start_page = _page_for_piece(piece, buffer, section_pages[0])
            spanned = sorted(set(section_pages))
            idx = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{doc.drug_id}_c{idx}_p{start_page}",
                    drug_id=doc.drug_id,
                    filename=doc.filename,
                    section=current_section,
                    page=start_page,
                    pages=spanned,
                    text=piece,
                )
            )
        buffer = []

    for page, line in _flatten_lines(doc):
        heading = _detect_heading(line)
        if heading:
            flush()
            current_section = heading
            # Keep the heading itself with the section body so it is searchable.
            buffer.append((page, line))
        else:
            buffer.append((page, line))
    flush()
    return chunks


def _page_for_piece(piece: str, buffer: List[tuple[int, str]], default_page: int) -> int:
    """Find the page of the first buffered line that appears in `piece`."""
    head = piece[:60].strip()
    if head:
        for page, line in buffer:
            token = line[:60].strip()
            if token and (token in piece or head in line):
                return page
    return default_page
