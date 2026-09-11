"""
Auto-correct typos in the user's question before searching.

Users mistype medical words ("pharmcokintics", "admistration", "dosrage").
We fix each word two ways, most reliable first:
  1. A small dictionary of common medical/typo fixes.
  2. The document's OWN vocabulary — if a typed word isn't a real word in the
     loaded PDFs, we snap it to the closest word that IS (difflib), but only on
     a high-confidence match so we never change a correct word.

This improves accuracy/precision: the search sees the right words, so it finds
the right section instead of missing it because of a spelling slip.
"""
from __future__ import annotations

import difflib
import re
from typing import List, Set

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]+")

# Known common misspellings → correct spelling (lowercase).
COMMON_FIXES = {
    "pharmcokintics": "pharmacokinetics",
    "pharmacokintics": "pharmacokinetics",
    "pharmokinetics": "pharmacokinetics",
    "admistration": "administration",
    "adminstration": "administration",
    "administraion": "administration",
    "dosrage": "dosage",
    "dosge": "dosage",
    "dosagee": "dosage",
    "sideffects": "side effects",
    "side-effects": "side effects",
    "sideeffects": "side effects",
    "contraindiction": "contraindication",
    "contraindicaton": "contraindication",
    "indiction": "indication",
    "indcation": "indication",
    "pregnency": "pregnancy",
    "pregancy": "pregnancy",
    "warining": "warning",
    "warnings": "warnings",
    "interation": "interaction",
    "interactons": "interactions",
    "pediatic": "pediatric",
    "peditric": "pediatric",
    "adverce": "adverse",
    "advrse": "adverse",
    "recomended": "recommended",
    "recommeded": "recommended",
    "storag": "storage",
    "overdos": "overdose",
    "symtoms": "symptoms",
    "symptomps": "symptoms",
}


def correct_query(query: str, vocabulary: Set[str]) -> str:
    """Return the query with obvious typos fixed. `vocabulary` is the set of
    real lowercase words found in the loaded PDFs."""
    if not query:
        return query

    def fix_word(w: str) -> str:
        low = w.lower()
        if low in COMMON_FIXES:
            return COMMON_FIXES[low]
        # Short words and real words are left alone.
        if len(low) < 5 or low in vocabulary:
            return w
        # Snap to the closest real word in the document, high confidence only.
        match = difflib.get_close_matches(low, vocabulary, n=1, cutoff=0.86)
        return match[0] if match else w

    return _WORD.sub(lambda m: fix_word(m.group(0)), query)


def build_vocabulary(texts: List[str]) -> Set[str]:
    """All lowercase words (len >= 4) seen across the indexed PDF text."""
    vocab: Set[str] = set()
    for t in texts:
        for w in _WORD.findall(t.lower()):
            if len(w) >= 4:
                vocab.add(w)
    return vocab
