"""
Hybrid retriever: mix "exact words" (BM25) with "meaning" (TF-IDF cosine).

- BM25 catches drug names and exact section words.
- TF-IDF cosine catches a question asked in different words.
We normalise each ranker to 0..1 and blend them, so neither can dominate just
because its raw numbers are on a different scale.

Search is always locked to one drug (the `drug_filter` from the UI). A question
about one medicine is never answered from another medicine's PDF.

The retriever is the single source of truth for page numbers: every hit carries
the real page from the index, and the answer layer is only ever allowed to cite
a page that appears in these hits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .. import config
from .bm25 import BM25, tokenize
from .index import load_index
from .synonyms import expand_query
from .spellfix import build_vocabulary, correct_query


@dataclass
class Hit:
    chunk_id: str
    drug_id: str
    filename: str
    section: str
    page: int
    pages: List[int]
    text: str
    score: float          # blended 0..1
    bm25: float
    semantic: float


# ---------------------------------------------------------------------------
# Section intent. Every US prescribing label follows the same FDA section
# layout, so what a question asks for tells us which heading should answer it:
# "who should not take" -> CONTRAINDICATIONS, "side effects" -> ADVERSE
# REACTIONS. This is label structure, not knowledge of any one medicine.
# Each entry: (pattern on the lowercase question, pattern on a section heading).
# ---------------------------------------------------------------------------
_SECTION_INTENTS = [
    (re.compile(r"\bindicat|\bused (for|to)\b|\bwhat is \S+ for\b|\btreat(s|ed|ing)?\b|\bpurpose\b|"
                r"\bwhat (infections|conditions|diseases)\b"),
     re.compile(r"\bINDICATIONS\b", re.I)),
    (re.compile(r"\bdos(e|es|ed|age|ing)\b|\bhow (much|often)\b|"
                r"\bhow (should|do|to|is|are)\b.*\b(take|taken|use|used|given|administered)\b|\badministr"),
     re.compile(r"DOSAGE AND ADMINISTRATION|Recommended Dosage|\bDosing\b|Administration Instructions", re.I)),
    (re.compile(r"\bcontraindicat|\bshould not (take|use|be)\b|\bwho (should|can) ?not\b|"
                r"\bwho (can't|cannot|shouldn't)\b"),
     re.compile(r"CONTRAINDICATIONS", re.I)),
    (re.compile(r"\bwarn|\bprecaution|\brisks?\b|\bdanger"),
     re.compile(r"^\s*5(\.\d+)?\s|WARNINGS|PRECAUTIONS", re.I)),
    (re.compile(r"\bside[- ]?effects?\b|\badverse\b|\breactions?\b"),
     re.compile(r"ADVERSE REACTIONS|Clinical Trials Experience|Postmarketing", re.I)),
    (re.compile(r"\binteract|\bwith other (drugs|medicines|medications)\b|\btogether with\b"),
     re.compile(r"DRUG INTERACTIONS|^\s*7(\.\d+)?\s", re.I)),
    (re.compile(r"\bpregnan|\bbreast|\blactat|\bnursing\b|\bfetus|\bunborn"),
     re.compile(r"Pregnancy|Lactation|SPECIFIC POPULATIONS|Embryo-Fetal", re.I)),
    (re.compile(r"\bchild|\bkids?\b|\bpediatric|\binfants?\b|\bteen"),
     re.compile(r"Pediatric Use|SPECIFIC POPULATIONS", re.I)),
    (re.compile(r"\belderly\b|\bgeriatric|\bolder (people|adults|patients)\b|\bseniors?\b"),
     re.compile(r"Geriatric Use|SPECIFIC POPULATIONS", re.I)),
    (re.compile(r"\bkidney|\brenal\b"),
     re.compile(r"Renal Impairment|SPECIFIC POPULATIONS", re.I)),
    (re.compile(r"\bliver\b|\bhepatic\b"),
     re.compile(r"Hepatic Impairment|SPECIFIC POPULATIONS", re.I)),
    (re.compile(r"\boverdos|\btoo (much|many)\b|\b\d+\s*(tablets?|capsules?|pills?|doses?)\b|"
                r"\bmore than (the )?(recommended|prescribed)\b"),
     re.compile(r"OVERDOSAGE|^\s*10(\.\d+)?\s", re.I)),
    (re.compile(r"\bstor(e|ed|age|ing)\b|\bhow supplied\b"),
     re.compile(r"HOW SUPPLIED|STORAGE", re.I)),
    (re.compile(r"\bhow does\b.*\bwork\b|\bmechanism\b"),
     re.compile(r"Mechanism of Action|CLINICAL PHARMACOLOGY", re.I)),
]

# Summary sections that mention every topic briefly (see SUMMARY_PENALTY).
_COUNSELING = re.compile(r"PATIENT COUNSELING", re.I)

# Words too generic to say anything about which heading is meant.
_GENERIC_TERMS = {
    "information", "patient", "patients", "label", "labels", "prescribing",
    "medicine", "medicines", "medication", "medications", "drugs", "people",
    "someone", "happens", "happen", "taking", "using", "known", "cause", "causes",
}

# Asking-words that carry no topic ("tell me", "write a", "explain").
_REQUEST_WORDS = {
    "tell", "give", "show", "explain", "know", "want", "need", "help", "please",
    "write", "make", "find", "list", "describe", "mean", "means",
}

# Everyday words that are clearly about taking a medicine even when they do not
# appear in any label ("sleepy", "forgot my pill", "is this pdf...").
_DOMAIN_HINT = re.compile(
    r"\b(pdf|label|leaflet|document|medicin|medicat|drugs?\b|tablet|capsul|pills?\b|"
    r"doctor|pharmac|symptom|allerg|alcohol|food|drink|driv|sleep|drows|dizz|tired|"
    r"pain|rash|sick|vomit|nause|missed|forgot|safe)"
)


def _minmax(values: List[float]) -> List[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


class Retriever:
    """Loads the index once and answers ranked queries against it."""

    def __init__(self, index: Optional[Dict] = None):
        self.index = index if index is not None else load_index()
        self.chunks: List[Dict] = self.index.get("chunks", [])
        self.documents: Dict[str, Dict] = self.index.get("documents", {})

        texts = [c["text"] for c in self.chunks]
        # Semantic ranker: TF-IDF over words + short phrases (1-2 grams).
        self._tfidf = None
        self._matrix = None
        if texts:
            self._tfidf = TfidfVectorizer(
                lowercase=True, ngram_range=(1, 2), min_df=1, stop_words="english"
            )
            self._matrix = self._tfidf.fit_transform(texts)
        # Lexical ranker.
        self._bm25 = BM25([tokenize(t) for t in texts]) if texts else None
        # Vocabulary of real words in the PDFs, used to auto-correct typos.
        self._vocab = build_vocabulary(texts) if texts else set()

    # -- info helpers -------------------------------------------------------
    def _key(self, owner: Optional[str], drug_id: str) -> str:
        owner_str = owner or "anonymous"
        return f"{owner_str}::{drug_id}"

    def _readable_owners(self, owner: Optional[str]) -> List[str]:
        """Who this user may read: the built-in shared library, plus their own
        private uploads. A user never sees ANOTHER user's private PDFs."""
        owners = [config.SHARED_OWNER]
        if owner and owner != config.SHARED_OWNER:
            owners.append(owner)
        return owners

    def has_drug(self, drug_id: str, owner: Optional[str] = None) -> bool:
        return self.document(drug_id, owner) is not None

    def document(self, drug_id: str, owner: Optional[str] = None) -> Optional[Dict]:
        """The user's own copy wins over the shared one if both exist.
        A missing owner counts as "anonymous" (see _key), who can still read
        the shared library."""
        own = self.documents.get(self._key(owner, drug_id))
        if own:
            return own
        return self.documents.get(self._key(config.SHARED_OWNER, drug_id))

    def documents_for(self, owner: str) -> List[Dict]:
        """The shared built-in library plus this user's own private uploads.
        If the user uploaded their own version of a shared drug, theirs wins."""
        own = {d["drug_id"]: d for d in self.documents.values() if d.get("owner") == owner}
        shared = {
            d["drug_id"]: d for d in self.documents.values()
            if d.get("owner") == config.SHARED_OWNER
        }
        merged = {**shared, **own}
        return sorted(merged.values(), key=lambda d: (d.get("owner") != config.SHARED_OWNER,
                                                      d.get("title", "")))

    # -- the search --------------------------------------------------------
    def _section_boost(self, query: str, candidate_idx: List[int], blended: List[float],
                       drug_id: Optional[str], doc_pages: int) -> List[float]:
        """Re-rank using the label's section headings.

        Word overlap alone lets summaries win: Highlights (page 1) and Patient
        Counseling mention every topic, so "who should not take X" matched
        counseling text instead of 4 CONTRAINDICATIONS. Here a chunk whose
        heading fits the question's intent is lifted, a heading that contains
        one of the question's own words gets a smaller lift, and — only when a
        specific section is wanted — summary chunks are nudged down.
        """
        q = query.lower()
        wanted = [heading for q_re, heading in _SECTION_INTENTS if q_re.search(q)]
        drug = (drug_id or "").lower()
        terms = {
            t for t in re.findall(r"[a-z]{5,}", q)
            if t not in ENGLISH_STOP_WORDS and t not in _GENERIC_TERMS
            and t not in _REQUEST_WORDS and not (drug and t in drug)
        }
        if not wanted and not terms:
            return blended

        out = list(blended)
        for j, i in enumerate(candidate_idx):
            chunk = self.chunks[i]
            heading = chunk["section"]
            bonus = 0.0
            if wanted and any(h.search(heading) for h in wanted):
                bonus += config.SECTION_BOOST
            if terms and any(t in heading.lower() for t in terms):
                bonus += config.HEADING_TERM_BOOST
            if wanted:
                if int(chunk["page"]) == 1 and doc_pages > 3:
                    bonus -= config.SUMMARY_PENALTY
                if bonus <= 0 and _COUNSELING.search(heading):
                    bonus -= config.SUMMARY_PENALTY
            out[j] += bonus
        return out

    def is_on_topic(self, query: str) -> bool:
        """Is this plausibly a question about a medicine label?

        The keyword list in safety.py only catches the topics it names. This
        is the general check: a question is off-topic when most of its real
        content words appear in none of the loaded labels ("tell me a joke",
        "prime minister of India"). Anything with a label intent or an
        everyday medicine word is kept, and a question with no content words
        at all ("what is this about?") is given the benefit of the doubt.
        """
        q = query.lower()
        if any(q_re.search(q) for q_re, _ in _SECTION_INTENTS) or _DOMAIN_HINT.search(q):
            return True
        words = [
            w for w in re.findall(r"[a-z]+", q)
            if len(w) >= 4 and w not in ENGLISH_STOP_WORDS and w not in _REQUEST_WORDS
        ]
        if not words:
            return True
        known = sum(w in self._vocab for w in words)
        return known / len(words) > 0.5

    def correct(self, query: str) -> str:
        """Fix typos in a question ("wht" -> "what", "tht" -> "that").

        Used for retrieval AND for the text handed to the model, so a question
        full of shorthand is understood the same way it is searched.
        """
        return correct_query(query, self._vocab)

    def search(self, query: str, drug_id: Optional[str] = None,
               owner: Optional[str] = None, top_k: int = None) -> List[Hit]:
        top_k = top_k or config.TOP_K
        if not self.chunks or not query.strip():
            return []

        # Search is locked to the requested drug, and to what this user may read:
        # the shared built-in library plus their own uploads. When a drug exists
        # in BOTH, we pin to the single owning copy so one answer never mixes two
        # different PDFs of the same medicine.
        doc_pages = 0
        if drug_id is not None and owner is not None:
            doc = self.document(drug_id, owner)
            if not doc:
                return []
            effective_owner = doc.get("owner")
            doc_pages = int(doc.get("pages") or 0)
            candidate_idx = [
                i for i, c in enumerate(self.chunks)
                if c["drug_id"] == drug_id and c.get("owner") == effective_owner
            ]
        else:
            allowed = set(self._readable_owners(owner))
            candidate_idx = [
                i for i, c in enumerate(self.chunks)
                if (drug_id is None or c["drug_id"] == drug_id)
                and (owner is None or c.get("owner") in allowed)
            ]
        if not candidate_idx:
            return []

        # 1) Auto-correct typos against the document's real vocabulary, then
        # 2) expand lay wording ("side effects" -> "adverse reactions").
        corrected = self.correct(query)
        expanded = expand_query(corrected)
        bm_all = self._bm25.scores(expanded)
        q_vec = self._tfidf.transform([expanded])
        sem_all = linear_kernel(q_vec, self._matrix).ravel()

        bm = [bm_all[i] for i in candidate_idx]
        sem = [float(sem_all[i]) for i in candidate_idx]
        bm_n = _minmax(bm)
        sem_n = _minmax(sem)

        w = config.LEXICAL_WEIGHT
        blended = [w * bm_n[j] + (1 - w) * sem_n[j] for j in range(len(candidate_idx))]
        # 3) Prefer the section the question is actually about.
        blended = self._section_boost(corrected, candidate_idx, blended, drug_id, doc_pages)

        order = sorted(range(len(candidate_idx)), key=lambda j: blended[j], reverse=True)
        hits: List[Hit] = []
        for j in order[:top_k]:
            i = candidate_idx[j]
            c = self.chunks[i]
            hits.append(
                Hit(
                    chunk_id=c["id"],
                    drug_id=c["drug_id"],
                    filename=c["filename"],
                    section=c["section"],
                    page=int(c["page"]),
                    pages=[int(p) for p in c.get("pages", [c["page"]])],
                    text=c["text"],
                    score=round(blended[j], 4),
                    bm25=round(bm[j], 4),
                    semantic=round(sem[j], 4),
                )
            )
        return hits
