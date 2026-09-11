"""
A small, dependency-free BM25 ranker.

BM25 is the "exact words" search. It is what catches drug names and section
words that a meaning-only search would miss. Implemented in plain Python so the
project needs no extra package to run.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import List

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus_tokens
        self.n = len(corpus_tokens)
        self.doc_len = [len(d) for d in corpus_tokens]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.freqs: List[Counter] = [Counter(d) for d in corpus_tokens]
        # Document frequency per term.
        df: Counter = Counter()
        for f in self.freqs:
            df.update(f.keys())
        # BM25+ idf (never negative).
        self.idf = {
            t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()
        }

    def scores(self, query: str) -> List[float]:
        q = tokenize(query)
        out = [0.0] * self.n
        if not self.n:
            return out
        for i in range(self.n):
            f = self.freqs[i]
            dl = self.doc_len[i] or 1
            s = 0.0
            for term in q:
                tf = f.get(term)
                if not tf:
                    continue
                idf = self.idf.get(term, 0.0)
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (tf * (self.k1 + 1)) / denom
            out[i] = s
        return out
