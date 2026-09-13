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


def _clean_markdown(text: str) -> str:
    """The model sometimes emits **bold** and exotic unicode spaces. The UI
    renders plain text, so strip both and normalise citation markers to
    the exact "[p. N]" form the verifier expects."""
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)     # **bold** -> bold
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", text)  # *italic* -> italic
    text = text.replace(" ", " ").replace(" ", " ")  # narrow/nbsp
    text = re.sub(r"\[p\.\s*", "[p. ", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


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
    "1. Answer the SPECIFIC question asked — nothing more. If the question is about "
    "pregnancy, answer only about pregnancy. If it is about dosage, answer only about "
    "dosage. Do NOT dump general information from every piece; ignore pieces that do "
    "not directly address the question, even if they were retrieved.\n"
    "2. Use only facts found in the pieces. Never add outside knowledge.\n"
    "3. After every fact, cite the page it came from using the exact form [p. N], "
    "where N is the 'page' shown for that piece.\n"
    "4. If the pieces only partly cover the question, answer what they do cover and "
    "say plainly what is not stated. Do not invent.\n"
    "5. Never tell the person what to do or take. State what the label says.\n"
    "6. Be concise: 2-4 short sentences, focused strictly on the question. No preamble, "
    "no summary of the medicine, no unrelated safety information.\n"
    "Only cite page numbers that appear in the pieces."
)


def _format_context(hits: List[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(f"[piece {i} | page {h.page} | section: {h.section}]\n{h.text}")
    return "\n\n".join(lines)


def groq_answer(query: str, hits: List[Hit], weak: bool = False) -> str:
    """Call Groq. Raises on any failure so the caller can fall back.

    Note on reasoning models (e.g. gpt-oss-20b): the model spends tokens on a
    hidden reasoning pass BEFORE writing its reply. If max_tokens is small the
    reasoning can consume the whole budget and the reply comes back EMPTY. We
    therefore keep reasoning_effort low and leave plenty of room for the answer,
    and retry once if the reply is still empty.
    """
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
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]

    def _call(**extra) -> str:
        resp = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=config.AI_MAX_TOKENS,
            **extra,
        )
        usage = getattr(resp, "usage", None)
        if usage:
            # One line per AI call, so the daily token budget can be watched in
            # the server log (Groq free tier: 200,000 tokens/day per account).
            print(f"[llm] tokens: {usage.prompt_tokens} in + {usage.completion_tokens} out "
                  f"= {usage.total_tokens}")
        return (resp.choices[0].message.content or "").strip()

    # reasoning_effort is only supported by reasoning models; ignore if rejected.
    try:
        text = _call(reasoning_effort=config.AI_REASONING_EFFORT)
    except Exception:
        text = _call()

    if not text:  # reasoning ate the budget — one retry with more room
        try:
            text = _call(reasoning_effort="low")
        except Exception:
            text = _call()
    return _clean_markdown(text)


def write_answer_with_mode(query: str, hits: List[Hit], weak: bool = False) -> tuple[str, str]:
    """Use Groq if configured, otherwise the extractive fallback.

    Returns (text, mode) where mode is "llm" or "extractive", so anything
    measuring answer quality can tell when the AI was not the one answering.

    The fallback is a real quality drop (concatenated label sentences rather
    than a focused answer), so we log WHY it happened instead of failing
    silently — a silent fallback previously looked like a bad AI answer.
    """
    if config.USE_LLM:
        try:
            text = groq_answer(query, hits, weak=weak)
            if text:
                return text, "llm"
            print("[llm] Groq returned empty content — using extractive fallback.")
        except Exception as e:
            print(f"[llm] Groq call failed ({type(e).__name__}: {e}) — using extractive fallback.")
    return extractive_answer(query, hits, weak=weak), "extractive"


def write_answer(query: str, hits: List[Hit], weak: bool = False) -> str:
    """The answer text only. See write_answer_with_mode."""
    return write_answer_with_mode(query, hits, weak=weak)[0]
