"""
Query expansion for everyday medical wording.

Users type "side effects", but a drug label says "adverse reactions". Users say
"how much", the label says "dosage". Without help, an exact-word search misses
these. We expand the query with the label's own vocabulary so a plain-English
question still finds the right section — and so we can give a related answer
instead of a flat "I don't know".

We only ADD words; we never remove the user's own words.
"""
from __future__ import annotations

import re

# lay phrase -> extra words to add to the search query
_EXPANSIONS = {
    r"\bside[- ]?effects?\b": "adverse reactions",
    r"\badverse\b": "adverse reactions side effects",
    r"\bhow much\b": "dosage dose recommended",
    r"\bdose[sd]?\b": "dosage recommended",
    r"\bdosing\b": "dosage recommended",
    r"\bwarn(ing|ings)?\b": "warnings precautions boxed",
    r"\bprecautions?\b": "warnings precautions",
    r"\binteractions?\b": "drug interactions",
    r"\bused? for\b": "indications usage treatment",
    r"\bindication\b": "indications usage",
    r"\btreat(s|ment|ing)?\b": "indications usage",
    r"\bchild(ren)?\b": "pediatric",
    r"\bkids?\b": "pediatric",
    r"\bpediatric\b": "pediatric children",
    r"\binfants?\b": "pediatric neonatal",
    r"\belderly\b": "geriatric older",
    r"\bold(er)? (people|patients|adults)\b": "geriatric",
    r"\bpregnan(t|cy)\b": "pregnancy lactation specific populations",
    r"\bbreast[- ]?feed(ing)?\b": "lactation nursing",
    r"\bstore|storage\b": "how supplied storage handling",
    r"\boverdose\b": "overdosage",
    r"\bcontraindicat(ed|ion|ions)?\b": "contraindications should not",
    r"\bshould not (take|use)\b": "contraindications",
    r"\bmissed dose\b": "missed dose administration",
    r"\bkidney\b": "renal impairment",
    r"\bliver\b": "hepatic impairment",
}


def expand_query(query: str) -> str:
    q = query.lower()
    extra = []
    for pattern, words in _EXPANSIONS.items():
        if re.search(pattern, q):
            extra.append(words)
    if not extra:
        return query
    return query + " " + " ".join(extra)
