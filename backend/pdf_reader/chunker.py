"""
Split medicine-label PDFs into searchable, section-aware chunks.

The chunker preserves:
    - drug_id
    - filename
    - section heading
    - citation page
    - every page covered by the chunk
    - source text

Why section-aware chunking?
----------------------------
Medicine labels contain clinically important sections such as:

    1 INDICATIONS AND USAGE
    2 DOSAGE AND ADMINISTRATION
    5 WARNINGS AND PRECAUTIONS
    6 ADVERSE REACTIONS
    8.4 Pediatric Use
    BOXED WARNING

Splitting only by a fixed character count can separate related
information and can make citations difficult to verify.

This implementation:
    1. Detects numbered and named section headings.
    2. Keeps headings with their section content.
    3. Preserves page provenance.
    4. Splits large sections at paragraph/sentence boundaries.
    5. Adds a small overlap between consecutive chunks.
    6. Avoids producing very small chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .reader import PdfDocument


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

# Examples:
#   1 INDICATIONS AND USAGE
#   2.1 Recommended Dosage
#   5 WARNINGS AND PRECAUTIONS
#   8.4 Pediatric Use
_NUM_HEADING = re.compile(
    r"^\s*(\d{1,2}(?:\.\d{1,2}){0,2})\s+([A-Z][A-Za-z].{2,80})$"
)

# Examples:
#   BOXED WARNING
#   CONTRAINDICATIONS
#   ADVERSE REACTIONS
_NAMED_HEADING = re.compile(
    r"^\s*(BOXED WARNING[S]?|WARNING[S]?|CONTRAINDICATION[S]?|"
    r"INDICATIONS AND USAGE|DOSAGE AND ADMINISTRATION|ADVERSE REACTIONS|"
    r"DRUG INTERACTIONS|USE IN SPECIFIC POPULATIONS|OVERDOSAGE|"
    r"HOW SUPPLIED|DESCRIPTION|CLINICAL PHARMACOLOGY|"
    r"PATIENT COUNSELING INFORMATION)\s*[:.]?\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Chunk configuration
# ---------------------------------------------------------------------------

MAX_CHARS = 1100
OVERLAP_CHARS = 120
MIN_CHUNK_CHARS = 40


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    id: str
    drug_id: str
    filename: str
    section: str
    page: int
    pages: List[int] = field(default_factory=list)
    text: str = ""


# ---------------------------------------------------------------------------
# Heading utilities
# ---------------------------------------------------------------------------

def _detect_heading(line: str) -> str | None:
    """Return a normalized heading if the line looks like a section heading."""

    line = line.strip()

    if not line or len(line) > 90:
        return None

    match = _NUM_HEADING.match(line)

    if match:
        number = match.group(1)
        title = match.group(2).strip()
        return f"{number} {title}"

    match = _NAMED_HEADING.match(line)

    if match:
        return line.strip(" :.").upper()

    return None


# ---------------------------------------------------------------------------
# PDF line handling
# ---------------------------------------------------------------------------

def _flatten_lines(doc: PdfDocument):
    """
    Yield (page, line) pairs in reading order.

    Raw page text is preferred because heading detection depends on
    real newline boundaries.
    """

    for page in doc.pages:
        source = page.raw if page.raw else page.text

        for line in source.split("\n"):
            line = line.strip()

            if line:
                yield page.page, line


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Normalize whitespace without changing the actual wording."""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _sentence_boundary(text: str, start: int, end: int) -> int:
    """
    Find a good sentence/paragraph boundary inside a character window.

    Prefer:
        1. Paragraph boundary
        2. Sentence ending
        3. Line-like punctuation
        4. Hard character boundary
    """

    if end >= len(text):
        return len(text)

    search_start = start + MAX_CHARS // 2

    # Prefer paragraph boundaries.
    paragraph_break = text.rfind("\n\n", search_start, end)

    if paragraph_break != -1:
        return paragraph_break

    # Sentence boundaries.
    sentence_matches = list(
        re.finditer(
            r"[.!?](?:[\"')\]]+)?\s+",
            text[search_start:end],
        )
    )

    if sentence_matches:
        match = sentence_matches[-1]
        return search_start + match.end()

    # Comma/semicolon/colon boundaries are better than cutting a word.
    punctuation = max(
        text.rfind("; ", search_start, end),
        text.rfind(": ", search_start, end),
        text.rfind(", ", search_start, end),
    )

    if punctuation != -1:
        return punctuation + 1

    # Fall back to a whitespace boundary.
    whitespace = text.rfind(" ", search_start, end)

    if whitespace != -1:
        return whitespace

    return end


def _split_text(text: str) -> List[tuple[str, int]]:
    """
    Split text into overlapping chunks.

    Returns:
        List of (chunk_text, character_start_offset).
    """

    text = _normalize_text(text)

    if len(text) <= MAX_CHARS:
        return [(text, 0)]

    pieces: List[tuple[str, int]] = []
    start = 0

    while start < len(text):
        end = min(start + MAX_CHARS, len(text))

        if end < len(text):
            end = _sentence_boundary(text, start, end)

        piece = text[start:end].strip()

        if piece:
            # Find the actual position after stripping whitespace.
            actual_start = start

            while (
                actual_start < len(text)
                and text[actual_start].isspace()
            ):
                actual_start += 1

            pieces.append((piece, actual_start))

        if end >= len(text):
            break

        next_start = end - OVERLAP_CHARS

        # Always move forward to prevent an infinite loop.
        start = max(next_start, start + 1)

    return pieces


# ---------------------------------------------------------------------------
# Page provenance
# ---------------------------------------------------------------------------

def _build_line_offsets(
    buffer: List[tuple[int, str]],
) -> List[tuple[int, int, int]]:
    """
    Build character ranges for each source line.

    Returns:
        (page, start_offset, end_offset)
    """

    ranges = []
    offset = 0

    for page, line in buffer:
        normalized = line.strip()

        if not normalized:
            continue

        start = offset
        end = start + len(normalized)

        ranges.append((page, start, end))

        # One space is inserted when joining lines.
        offset = end + 1

    return ranges


def _pages_for_range(
    start: int,
    end: int,
    line_ranges: List[tuple[int, int, int]],
    default_page: int,
) -> List[int]:
    """Return all physical PDF pages touched by a text range."""

    pages = []

    for page, line_start, line_end in line_ranges:
        if line_end >= start and line_start <= end:
            pages.append(page)

    if not pages:
        return [default_page]

    return sorted(set(pages))


def _page_for_start(
    start: int,
    line_ranges: List[tuple[int, int, int]],
    default_page: int,
) -> int:
    """Return the physical page where a chunk starts."""

    for page, line_start, line_end in line_ranges:
        if line_start <= start <= line_end:
            return page

    return default_page


# ---------------------------------------------------------------------------
# Main chunking logic
# ---------------------------------------------------------------------------

def chunk_document(doc: PdfDocument) -> List[Chunk]:
    """
    Turn a PDF document into section-aware chunks with page provenance.
    """

    chunks: List[Chunk] = []

    current_section = "PRESCRIBING INFORMATION"

    # Each entry is:
    #     (physical_page, source_line)
    buffer: List[tuple[int, str]] = []

    def flush() -> None:
        """Convert the current section buffer into searchable chunks."""

        nonlocal buffer

        if not buffer:
            return

        section_pages = [page for page, _ in buffer]

        body = " ".join(line for _, line in buffer)
        body = _normalize_text(body)

        if len(body) < MIN_CHUNK_CHARS:
            buffer = []
            return

        line_ranges = _build_line_offsets(buffer)

        for piece, offset in _split_text(body):

            if len(piece) < MIN_CHUNK_CHARS:
                continue

            piece_end = offset + len(piece)

            start_page = _page_for_start(
                offset,
                line_ranges,
                section_pages[0],
            )

            spanned_pages = _pages_for_range(
                offset,
                piece_end,
                line_ranges,
                section_pages[0],
            )

            # Ensure the citation page is always included.
            if start_page not in spanned_pages:
                spanned_pages.insert(0, start_page)

            spanned_pages = sorted(set(spanned_pages))

            chunk_number = len(chunks)

            chunks.append(
                Chunk(
                    id=(
                        f"{doc.drug_id}"
                        f"_c{chunk_number}"
                        f"_p{start_page}"
                    ),
                    drug_id=doc.drug_id,
                    filename=doc.filename,
                    section=current_section,
                    page=start_page,
                    pages=spanned_pages,
                    text=piece,
                )
            )

        buffer = []

    # -----------------------------------------------------------------------
    # Process the PDF line by line.
    # -----------------------------------------------------------------------

    for page, line in _flatten_lines(doc):

        heading = _detect_heading(line)

        if heading:
            # Finish the previous section first.
            flush()

            current_section = heading

            # Keep the heading searchable.
            buffer.append((page, line))

        else:
            buffer.append((page, line))

    # Flush the final section.
    flush()

    return chunks