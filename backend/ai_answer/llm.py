"""
Turn the retrieved PDF pieces into a written answer.

Two modes:
  1. Groq (if AI_API_KEY is set): the LLM writes the answer, but is told to use
     ONLY the numbered pieces and to cite each fact as [p. N] using the page
     numbers we give it. It decides nothing about the facts.
  2. Extractive fallback (no key needed): we build the answer directly from the
     retrieved sentences. Because every sentence is copied from a known chunk,
     its page number is provably correct. This is the safe default and also the
     backup if Groq is unavailable.

Either way, answer.py re-checks every [p. N] against the retrieved pages, so a
made-up page can never reach the user.
"""
from __future__ import annotations

import re
from typing import Dict, List

from .. import config
from ..search.hybrid import Hit

_SENT = re.compile(r"(?<=[.;:])\s+(?=[A-Z0-9])")


def _body_without_heading(text: str, section: str) -> str:
    """Remove the section heading the chunk starts with, using the known
    section string, so an extracted sentence reads as prose, not a heading."""
    body = text.strip()
    sec = (section or "").strip()
    if sec and body.lower().startswith(sec.lower()):
        body = body[len(sec):].strip(" :.-")
    # Also drop a generic all-caps "HIGHLIGHTS OF PRESCRIBING INFORMATION" lead.
    body = re.sub(r"^HIGHLIGHTS OF PRESCRIBING INFORMATION\s*", "", body, flags=re.I)
    return body.strip()


def _sentences(text: str) -> List[str]:
    parts = _SENT.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


# ---------------------------------------------------------------------------
# Extractive fallback (no external model)
# ---------------------------------------------------------------------------
def extractive_answer(query: str, hits: List[Hit], weak: bool = False) -> str:
    """Compose an answer from the retrieved sentences, tagging real pages.

    We pick the sentences that best overlap the question from the top hits,
    keep them in ranked order, and append [p. N] with the page the sentence's
    chunk really came from.
    """
    q_words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2}
    picked: List[tuple[str, int]] = []
    seen_sentences: set[str] = set()

    for hit in hits:
        body = _body_without_heading(hit.text, hit.section)
        best_sent, best_overlap = None, 0
        for s in _sentences(body):
            key = s.lower()[:80]
            if key in seen_sentences:
                continue
            overlap = len(q_words & set(re.findall(r"[a-z0-9]+", s.lower())))
            if overlap > best_overlap:
                best_overlap, best_sent = overlap, s
        # Fall back to the start of the chunk if nothing overlaps.
        if best_sent is None:
            sents = _sentences(body)
            best_sent = sents[0] if sents else body[:240]
        seen_sentences.add(best_sent.lower()[:80])
        sentence = best_sent.rstrip(".") + f" [p. {hit.page}]."
        picked.append((sentence, hit.page))
        if len(picked) >= min(3, len(hits)):
            break

    body = " ".join(s for s, _ in picked)
    if weak:
        body = (
            "The prescribing information does not directly answer this, but the "
            "closest related text is: " + body
        )
    return body


# ---------------------------------------------------------------------------
# Groq mode
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are MedCite, a careful assistant that answers questions about a medicine "
    "using ONLY the numbered document pieces provided. Rules you must follow:\n"
    "1. Use only facts found in the pieces. Never add outside knowledge.\n"
    "2. After every fact, cite the page it came from using the exact form [p. N], "
    "where N is the 'page' shown for that piece.\n"
    "3. If the pieces only partly cover the question, answer what they do cover and "
    "say plainly what is not stated. Do not invent.\n"
    "4. Never tell the person what to do or take. State what the label says.\n"
    "5. Keep it to 2-4 short sentences.\n"
    "Only cite page numbers that appear in the pieces."
)


def _format_context(hits: List[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(f"[piece {i} | page {h.page} | section: {h.section}]\n{h.text}")
    return "\n\n".join(lines)


def groq_answer(query: str, hits: List[Hit], weak: bool = False) -> str:
    """Call Groq. Raises on any failure so the caller can fall back."""
    from groq import Groq  # imported lazily; only needed in this mode

    client = Groq(api_key=config.AI_API_KEY)
    context = _format_context(hits)
    hint = (
        "\n\nNote: these pieces may not directly answer the question. If so, give "
        "the closest related label information and say it is related, not exact."
        if weak else ""
    )
    user = (
        f"Question: {query}\n\nDocument pieces:\n{context}{hint}\n\n"
        "Write the answer now, citing pages as [p. N]."
    )
    resp = client.chat.completions.create(
        model=config.AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=400,
    )
    return (resp.choices[0].message.content or "").strip()


def write_answer(query: str, hits: List[Hit], weak: bool = False) -> str:
    """Use Groq if configured, otherwise the extractive fallback."""
    if config.USE_LLM:
        try:
            text = groq_answer(query, hits, weak=weak)
            if text:
                return text
        except Exception:
            # Any Groq error (rate limit, network, bad key) -> safe fallback.
            pass
    return extractive_answer(query, hits, weak=weak)
