"""
Orchestrate one question: search -> decide -> write -> verify.

This module enforces the three guarantees the product needs:

  * Correct pages    - a citation's page is the real page the chunk came from.
  * No duplicates    - the citation list has one entry per page.
  * Answer and source match - every [p. N] left in the answer text also appears
                       in the citation list, and vice-versa; a page the model
                       invents (not in the retrieved pieces) is stripped out.

It also implements the "say something related instead of a flat no" behaviour:
when the match is weak but present, we still answer, from the closest text, and
label it as related.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .. import config
from ..search.hybrid import Hit, Retriever
from . import safety
from .llm import write_answer_with_mode

_CITE = re.compile(r"\[p\.\s*(\d+)(?:\s*,\s*(\d+))?\]")


def _snippet(text: str, limit: int = 200) -> str:
    """Collapse whitespace and trim text to about `limit` characters, ending on a sentence where possible."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(". ")
    return (cut[: dot + 1] if dot > 60 else cut).strip() + "…"


def _collapse_adjacent_cites(answer: str) -> str:
    """Merge citations that sit next to each other with no words between them,
    e.g. "... once daily [p. 8]. [p. 2]." -> "... once daily [p. 8, 2].".
    Avoids the ugly empty-clause the LLM sometimes produces."""
    pattern = re.compile(r"\[p\.\s*(\d+)\s*\]\s*[.,;]?\s*\[p\.\s*(\d+)\s*\]")
    prev = None
    while prev != answer:
        prev = answer
        answer = pattern.sub(r"[p. \1, \2]", answer)
    # tidy any leftover " . " and doubled spaces
    answer = re.sub(r"\s+([.,;])", r"\1", answer)
    answer = re.sub(r"\.\s*\.", ".", answer)
    answer = re.sub(r"\s{2,}", " ", answer).strip()
    return answer


def _pages_in_answer(answer: str) -> List[int]:
    """Return every page number cited in the answer's [p. N] / [p. N, M] markers."""
    pages: List[int] = []
    for m in _CITE.finditer(answer):
        pages.append(int(m.group(1)))
        if m.group(2):
            pages.append(int(m.group(2)))
    return pages


def _strip_unverified_pages(answer: str, allowed: set[int]) -> str:
    """Remove any [p. N] whose page is not in the retrieved set."""
    def repl(m: re.Match) -> str:
        """Keep only cited pages that were actually retrieved; drop the marker if none were."""
        good = [g for g in (m.group(1), m.group(2)) if g and int(g) in allowed]
        if not good:
            return ""  # drop a fully made-up citation marker
        if len(good) == 1:
            return f"[p. {good[0]}]"
        return f"[p. {good[0]}, {good[1]}]"
    cleaned = _CITE.sub(repl, answer)
    # tidy double spaces / space-before-period left by removals
    cleaned = re.sub(r"\s+([.,;])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def _build_citations(answer: str, hits: List[Hit]) -> List[Dict]:
    """One citation per page, in the order the pages appear in the answer.

    The page, section and text all come straight from the retrieved chunk, so
    the citation the user clicks matches both the answer and the real PDF page.
    """
    # Best hit per page (highest score wins if a page appears in several hits).
    best_by_page: Dict[int, Hit] = {}
    for h in hits:
        cur = best_by_page.get(h.page)
        if cur is None or h.score > cur.score:
            best_by_page[h.page] = h

    ordered_pages: List[int] = []
    for p in _pages_in_answer(answer):
        if p in best_by_page and p not in ordered_pages:
            ordered_pages.append(p)
    # If the answer somehow has no marker, fall back to the top hit's page.
    if not ordered_pages and hits:
        ordered_pages = [hits[0].page]

    citations: List[Dict] = []
    for p in ordered_pages[: config.MAX_CITATIONS]:
        h = best_by_page.get(p) or hits[0]
        citations.append(
            {"page": p, "section": h.section, "text": _snippet(h.text), "file": h.filename}
        )
    return citations


def _select_context(hits: List[Hit]) -> List[Hit]:
    """The pieces actually sent to the AI (see CONTEXT_MARGIN in config.py).

    Keeps the top MIN_CONTEXT_PIECES, plus any further piece scoring within
    CONTEXT_MARGIN of the best one. A clear winner costs ~3 pieces of tokens; a
    close race still sends up to TOP_K so the right section is not cut off.
    """
    if not hits:
        return hits
    best = hits[0].score
    return [h for i, h in enumerate(hits)
            if i < config.MIN_CONTEXT_PIECES or h.score >= best - config.CONTEXT_MARGIN]


def answer_question(
    question: str,
    history: Optional[List[Dict]] = None,
    drug_filter: Optional[str] = None,
    retriever: Optional[Retriever] = None,
    user_id: Optional[str] = None,
    llm_allowed: bool = True,
) -> Dict:
    """Answer one question end to end: rewrite follow-ups, run safety checks, search the PDF, write the answer and verify its citations."""
    history = history or []
    retriever = retriever or Retriever()
    user_id = user_id or "anonymous"

    doc = retriever.document(drug_filter, user_id) if drug_filter else None
    drug_name = doc["title"] if doc else (drug_filter or "this medicine").upper()
    source_pdf = doc["filename"] if doc else None
    has_drug = bool(doc)

    # 0. Greetings / thanks / "what can you do" -> friendly reply, no retrieval.
    kind = safety.detect_smalltalk(question)
    if kind:
        return {**safety.smalltalk_response(kind, drug_name, has_drug), "source_pdf": source_pdf}

    # 1. No document loaded for this drug -> honest refusal.
    if drug_filter and not retriever.has_drug(drug_filter, user_id):
        return {**safety.refusal_no_document(drug_name), "source_pdf": None}

    # 2. Clearly outside a drug label -> refuse. The keyword list catches the
    #    obvious topics; is_on_topic catches the rest by checking the question's
    #    words against what the loaded labels actually contain.
    if safety.is_out_of_domain(question) or not retriever.is_on_topic(retriever.correct(question)):
        return {**safety.refusal_out_of_domain(drug_name), "source_pdf": source_pdf}

    # 3. Resolve short follow-ups against the chat, fix typos, then search.
    # The corrected text is what the model sees too — otherwise it would be
    # asked "wht happens if i take tht" while the search looked for the fixed
    # wording, and the two could disagree.
    resolved = retriever.correct(safety.rewrite_followup(question, history))
    hits = retriever.search(resolved, drug_id=drug_filter, owner=user_id, top_k=config.TOP_K)

    top_score = hits[0].score if hits else 0.0
    # Nothing at all worth showing -> refuse (but kindly).
    if not hits or top_score < config.FLOOR_SCORE:
        return {
            "is_refusal": True,
            "is_advice": safety.detect_advice(question),
            "refusal_reason": "The document does not contain information on this.",
            "answer": (
                f"I couldn't find anything about that in the {drug_name} prescribing "
                "information. It may not be covered in this label. Try rephrasing, or "
                "ask about the uses, dose, warnings, side effects or interactions."
            ),
            "section": None,
            "citations": [],
            "drug_name": drug_name,
            "source_pdf": source_pdf,
        }

    # 4. Weak but present -> answer from the closest text, marked as related.
    weak = top_score < config.WEAK_SCORE
    is_advice = safety.detect_advice(question)

    # 4b. Out of AI answers for today (see DAILY_QUESTION_LIMIT) -> say so
    #     instead of calling the AI. Greetings and refusals above stay free.
    if not llm_allowed:
        return {
            "is_refusal": True,
            "is_advice": is_advice,
            "limit_reached": True,
            "refusal_reason": "Daily question limit reached",
            "answer": (
                f"You've used all {config.DAILY_QUESTION_LIMIT} questions for today. "
                "Questions that have been asked before are still answered instantly, "
                "and your limit resets at midnight."
            ),
            "section": None,
            "citations": [],
            "drug_name": drug_name,
            "source_pdf": source_pdf,
            "answer_mode": None,
        }

    # Only these pieces go to the AI, so pages are verified against them too.
    context = _select_context(hits)
    raw, answer_mode = write_answer_with_mode(resolved, context, weak=weak)

    # 5. Verify: strip invented pages, then build a matching, de-duplicated
    #    citation list from the real chunks.
    allowed_pages = {h.page for h in context}
    verified = _strip_unverified_pages(raw, allowed_pages)
    verified = _collapse_adjacent_cites(verified)

    # Keep a failed or empty model response useful instead of returning only a
    # citation marker.
    if not re.sub(_CITE, "", verified).strip() and hits:
        verified = f"The label states: {_snippet(hits[0].text, limit=400)}"

    # If verification removed every citation, anchor to the top hit so the
    # answer still has a real source.
    if not _pages_in_answer(verified) and hits:
        verified = verified.rstrip(".") + f" [p. {hits[0].page}]."

    citations = _build_citations(verified, context)
    section = citations[0]["section"] if citations else (hits[0].section if hits else None)

    return {
        "is_refusal": False,
        "is_advice": is_advice,
        # "llm" normally; "extractive" when the AI was unavailable and the
        # backup writer answered instead.
        "answer_mode": answer_mode,
        "answer": verified,
        "section": section,
        "citations": citations,
        "drug_name": drug_name,
        "source_pdf": source_pdf,
    }
