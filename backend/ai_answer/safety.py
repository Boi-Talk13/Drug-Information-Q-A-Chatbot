"""
Responsible-AI helpers: follow-up rewriting, medical-advice detection, and the
exact wording used when we cannot answer.

Safety is a feature we build, not a footnote:
  - "No proof, no answer" is only used when there is essentially nothing in the
    document. When there is *related* text we prefer a correlated best-effort
    answer that says plainly it is related, not exact (this is what the product
    owner asked for: say something useful instead of a flat "no").
  - Advice questions ("should I stop this?") get the label text plus "ask a
    doctor", never a yes/no.
"""
from __future__ import annotations

import re
from typing import Dict, List

ADVICE_PATTERNS = [
    r"should i\b", r"may i\b", r"is it okay to\b",
    r"can i (stop|take|double|mix|skip|split|crush)",
    r"is it safe for me", r"what should i do", r"do i need to",
    r"my (doctor|symptoms|dose)", r"doctor told me", r"i feel", r"i am feeling",
    r"diagnose", r"prescribe (me|for me)", r"how much should i",
]

# Words that mean the question is not about a drug label at all.
OUT_OF_DOMAIN = [
    "stock price", "share price", "price in dollars", "who made", "ceo",
    "weather", "football", "recipe", "movie", "song", "capital of",
]

FOLLOWUP_STARTERS = (
    "and ", "what about", "for children", "in children", "for kids",
    "and for", "how about", "what if", "also", "then", "same for",
)


GREETING_WORDS = {
    "hi", "hii", "hiya", "hey", "heya", "hello", "helo", "yo", "hola", "namaste",
    "sup", "greetings", "there", "good", "morning", "afternoon", "evening", "gm",
}
THANKS_WORDS = {
    "thanks", "thank", "thankyou", "thx", "ty", "cool", "nice", "great", "ok",
    "okay", "okey", "awesome", "perfect", "good", "got", "it",
}
HELP_PHRASES = {
    "who are you", "what are you", "what is this", "what is medcite", "help",
    "what can you do", "what do you do", "how do you work", "how does this work",
    "what can i ask", "how to use", "how to use this",
}


def detect_smalltalk(query: str):
    """Return 'greeting' | 'thanks' | 'help' for chit-chat, else None."""
    words = re.findall(r"[a-z']+", query.lower())
    if not words or len(words) > 6:
        return None
    joined = " ".join(words)
    if joined in HELP_PHRASES:
        return "help"
    if all(w in GREETING_WORDS for w in words):
        return "greeting"
    if all(w in THANKS_WORDS for w in words):
        return "thanks"
    return None


def smalltalk_response(kind: str, drug_name: str, has_drug: bool) -> Dict:
    subject = drug_name if has_drug else "a medicine"
    examples = (
        f'Try: “What is the dose of {drug_name}?”, “What are the side effects?”, '
        f'or “What are the warnings?”'
    )
    if kind == "greeting":
        answer = (
            f"Hi! I'm MedCite. I answer questions about {subject} using only its "
            f"official prescribing label, and I show the exact page for every "
            f"answer. {examples}"
        )
    elif kind == "thanks":
        answer = "You're welcome! Ask me anything else about the medicine's label whenever you like."
    else:  # help
        answer = (
            "I'm MedCite, a document-grounded assistant. I read the official "
            f"prescribing PDF for {subject} and answer only from it, citing the "
            f"page for every fact — I never guess. {examples}"
        )
    return {
        "is_refusal": False,
        "is_advice": False,
        "answer": answer,
        "section": None,
        "citations": [],
        "drug_name": drug_name,
    }


def detect_advice(query: str) -> bool:
    q = query.lower()
    return any(re.search(p, q) for p in ADVICE_PATTERNS)


def is_out_of_domain(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in OUT_OF_DOMAIN)


def rewrite_followup(query: str, history: List[Dict]) -> str:
    """Turn a short follow-up ("and for children?") into a standalone question.

    We join it with the most recent user question so the search has enough
    words to find the right section. This is how the bot "remembers" the chat.
    """
    q = query.strip()
    ql = q.lower()
    is_short = len(q.split()) <= 6
    looks_like_followup = ql.startswith(FOLLOWUP_STARTERS) or is_short
    if not looks_like_followup or not history:
        return q

    last_user = ""
    for m in reversed(history):
        if m.get("role") == "user" and m.get("text", "").strip().lower() != ql:
            last_user = m["text"].strip()
            break
    if not last_user:
        return q
    # Keep both so drug/section words from the previous turn are searchable.
    return f"{last_user} {q}"


# ---------------------------------------------------------------------------
# Standard responses
# ---------------------------------------------------------------------------
def refusal_no_document(drug_name: str) -> Dict:
    return {
        "is_refusal": True,
        "is_advice": False,
        "refusal_reason": "No prescribing document is loaded for this medicine.",
        "answer": (
            f"I don't have the official prescribing document for {drug_name} loaded, "
            "so I can't answer from a verified source. I only answer from the medicine "
            "PDFs that have been indexed. Please upload that medicine's label, or pick a "
            "medicine from the list."
        ),
        "section": None,
        "citations": [],
        "drug_name": drug_name,
    }


def refusal_out_of_domain(drug_name: str) -> Dict:
    return {
        "is_refusal": True,
        "is_advice": False,
        "refusal_reason": "The question is outside what a drug label covers.",
        "answer": (
            "That's outside what a medicine label can tell us. I only answer questions "
            "about what the official prescribing information says — things like the uses, "
            "dose, warnings, side effects and interactions of the medicine."
        ),
        "section": None,
        "citations": [],
        "drug_name": drug_name,
    }
