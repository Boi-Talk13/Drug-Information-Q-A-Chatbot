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

# Single letters are matched too, so "y" -> "why" can be fixed. Only the
# explicit dictionary below ever rewrites them: the fuzzy matcher skips
# anything under 5 letters, so a real single-letter token (vitamin D,
# hepatitis C, T cells) is never touched unless it is listed by name.
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")

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
    "pregent": "pregnant",
    "pregnent": "pregnant",
    "pragnant": "pregnant",
    "pregnat": "pregnant",
    "pregnany": "pregnancy",
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

    # --- more medical words people mistype -------------------------------
    "tabelt": "tablet", "tablt": "tablet", "tabet": "tablet", "tablets": "tablets",
    "capsul": "capsule", "capsuls": "capsules",
    "medicin": "medicine", "medecine": "medicine", "medicene": "medicine",
    "meds": "medicine", "tabs": "tablets",
    "pateint": "patient", "patinet": "patient", "pateints": "patients",
    "adutls": "adults", "childrens": "children",
    "efect": "effect", "efects": "effects", "effct": "effect", "affects": "effects",
    "dizzyness": "dizziness", "nausia": "nausea", "vomitting": "vomiting",
    "diarrhoea": "diarrhea", "diarhea": "diarrhea", "diarrhea": "diarrhea",
    "headche": "headache", "headach": "headache",
    "alergy": "allergy", "allergi": "allergy", "alergic": "allergic",
    "infectin": "infection", "infextion": "infection",
    "presciption": "prescription", "prescribtion": "prescription",
    "treatmnt": "treatment", "treatement": "treatment",
    "injektion": "injection", "injction": "injection",
    "safty": "safety", "safte": "safety",
    "breastfeed": "breastfeeding", "breastfeading": "breastfeeding",
    "kidny": "kidney", "livr": "liver", "presure": "pressure",
    "bloodpressure": "blood pressure",

    # --- everyday shorthand and slips -------------------------------------
    # People type questions the way they text. These are short words, so the
    # fuzzy matcher below never touches them (it skips words under 5 letters
    # to avoid mangling real ones) — the only way to fix them is by name.
    "tht": "that", "taht": "that", "thta": "that",
    "wht": "what", "wat": "what", "whta": "what", "waht": "what",
    "teh": "the", "hte": "the", "th": "the",
    "adn": "and", "nad": "and", "nd": "and",
    "nt": "not", "dont": "don't", "doesnt": "doesn't", "cant": "can't",
    "isnt": "isn't", "wont": "won't", "shouldnt": "shouldn't",
    "frm": "from", "fr": "for", "fo": "for", "ofr": "for",
    "wit": "with", "wth": "with", "wih": "with",
    "cn": "can", "hv": "have", "hav": "have", "havve": "have",
    "ur": "your", "yr": "your", "youre": "you're",
    "pls": "please", "plz": "please",
    "bcz": "because", "bcoz": "because", "coz": "because",
    "becoz": "because", "becuase": "because", "becasue": "because",
    "wil": "will", "wll": "will",
    "shud": "should", "shoudl": "should", "shoud": "should",
    "cud": "could", "wud": "would", "wold": "would",
    "abt": "about", "aboyt": "about", "abut": "about",
    "whn": "when", "wen": "when", "whne": "when",
    "whr": "where", "wer": "where",
    "hw": "how", "hwo": "how",
    "alredy": "already", "alreday": "already",
    "releated": "related", "relatd": "related",
    "cirrently": "currently", "currenty": "currently",
    "remvoe": "remove", "wroking": "working", "workin": "working",
    "kepted": "kept", "recieve": "receive", "seperate": "separate",
    "occured": "occurred", "definately": "definitely",
    "usefull": "useful", "sucess": "success",
    "helpfull": "helpful", "carefull": "careful",

    # Single-letter texting shorthand. Deliberately NOT including a/b/c/d/e/k
    # (vitamin D, hepatitis C) or t (T cells) — those are real label terms.
    "u": "you", "y": "why", "r": "are",
}


def correct_query(query: str, vocabulary: Set[str]) -> str:
    """Return the query with obvious typos fixed. `vocabulary` is the set of
    real lowercase words found in the loaded PDFs."""
    if not query:
        return query

    def fix_word(w: str) -> str:
        """Correct one word: known shorthand first, then a close match from the document's own words."""
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
