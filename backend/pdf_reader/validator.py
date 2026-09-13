"""
Check that an uploaded PDF is actually a medicine's prescribing information —
not a resume, an invoice, a random report, or any other unrelated document.

We do NOT use the AI model for this (that would cost a call and could be
fooled). Instead we look for the section headings every real FDA-style drug
label carries. A genuine label always has several of these; an unrelated
document essentially never does.

This runs BEFORE the file is indexed, so a rejected upload never contaminates
a user's medicine library.
"""
from __future__ import annotations

from typing import Tuple

from .reader import PdfDocument

# Any ONE of these appearing is a very strong signal by itself — these phrases
# are close to unique to official prescribing information / medication guides.
STRONG_MARKERS = [
    "highlights of prescribing information",
    "full prescribing information",
    "prescribing information",
    "medication guide",
    "patient information leaflet",
    "package insert",
]

# The standard FDA label sections. A real label has most of these; we require
# several matches before trusting a document that lacks a STRONG marker.
SECTION_MARKERS = [
    "indications and usage",
    "dosage and administration",
    "contraindications",
    "warnings and precautions",
    "adverse reactions",
    "drug interactions",
    "use in specific populations",
    "clinical pharmacology",
    "how supplied",
    "patient counseling information",
    "boxed warning",
    "overdosage",
    "description",
    "nonclinical toxicology",
]

MIN_SECTION_MATCHES = 3   # needed when no STRONG_MARKER is present
SCAN_PAGES = 12           # only the first N pages — plenty for any real label


def looks_like_drug_label(doc: PdfDocument) -> Tuple[bool, str]:
    """Return (is_valid, reason). `reason` explains a rejection in plain words."""
    if not doc.pages:
        return False, "The PDF has no readable text (it may be a blank or scanned image)."

    sample = " ".join(p.text for p in doc.pages[:SCAN_PAGES]).lower()
    if len(sample.strip()) < 200:
        return False, "The PDF has almost no extractable text."

    strong_hit = next((m for m in STRONG_MARKERS if m in sample), None)
    if strong_hit:
        return True, ""

    matched = [m for m in SECTION_MARKERS if m in sample]
    if len(matched) >= MIN_SECTION_MATCHES:
        return True, ""

    return False, (
        "This doesn't look like a medicine's prescribing information (no "
        "sections like Indications and Usage, Dosage and Administration, "
        "Warnings, or Adverse Reactions were found). Please upload the "
        "official drug label / prescribing information PDF for this medicine."
    )
