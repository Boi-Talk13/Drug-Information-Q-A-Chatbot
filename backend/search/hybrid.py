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

from sklearn.feature_extraction.text import TfidfVectorizer
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
    def _key(self, owner: str, drug_id: str) -> str:
        return f"{owner}::{drug_id}"

    def has_drug(self, drug_id: str, owner: str) -> bool:
        return self._key(owner, drug_id) in self.documents

    def document(self, drug_id: str, owner: str) -> Optional[Dict]:
        return self.documents.get(self._key(owner, drug_id))

    def documents_for(self, owner: str) -> List[Dict]:
        """All documents owned by this user (their private library)."""
        return [d for d in self.documents.values() if d.get("owner") == owner]

    # -- the search --------------------------------------------------------
    def search(self, query: str, drug_id: Optional[str] = None,
               owner: Optional[str] = None, top_k: int = None) -> List[Hit]:
        top_k = top_k or config.TOP_K
        if not self.chunks or not query.strip():
            return []

        # Search is locked to the requested drug AND to this user's own PDFs.
        candidate_idx = [
            i for i, c in enumerate(self.chunks)
            if (drug_id is None or c["drug_id"] == drug_id)
            and (owner is None or c.get("owner") == owner)
        ]
        if not candidate_idx:
            return []

        # 1) Auto-correct typos against the document's real vocabulary, then
        # 2) expand lay wording ("side effects" -> "adverse reactions").
        corrected = correct_query(query, self._vocab)
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
