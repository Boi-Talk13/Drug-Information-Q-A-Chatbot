"""
Central configuration for the MedCite backend.

Configuration is loaded from environment variables with safe defaults.
Nothing in this module contains secrets; sensitive values such as
AI_API_KEY are read only from the environment.

The configuration also validates numeric settings so invalid environment
values do not cause confusing runtime failures.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from the project root when available."""

    env_path = PROJECT_ROOT / ".env"

    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
        return

    except Exception:
        # Fall back to a small parser when python-dotenv is unavailable.
        pass

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()

        for line in lines:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)

            os.environ.setdefault(
                key.strip(),
                value.strip().strip('"').strip("'"),
            )

    except OSError:
        # Configuration should not prevent the backend from starting.
        pass


def _get_int(
    name: str,
    default: int,
    minimum: int = 0,
) -> int:
    """
    Read an integer environment variable safely.

    If the value is missing or invalid, the default is used.
    """

    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)

    except ValueError:
        print(
            f"Warning: invalid {name}={raw_value!r}; "
            f"using default {default}."
        )
        return default

    if value < minimum:
        print(
            f"Warning: {name} must be >= {minimum}; "
            f"using default {default}."
        )
        return default

    return value


def _get_float(
    name: str,
    default: float,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    """
    Read a floating-point environment variable safely.
    """

    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = float(raw_value)

    except ValueError:
        print(
            f"Warning: invalid {name}={raw_value!r}; "
            f"using default {default}."
        )
        return default

    if value < minimum:
        print(
            f"Warning: {name} must be >= {minimum}; "
            f"using default {default}."
        )
        return default

    if maximum is not None and value > maximum:
        print(
            f"Warning: {name} must be <= {maximum}; "
            f"using default {default}."
        )
        return default

    return value


def _get_origins(default: str) -> list[str]:
    """
    Read and normalize allowed CORS origins.

    Empty values are ignored and duplicate origins are removed.
    """

    raw_origins = os.getenv("ALLOWED_ORIGINS", default)

    origins = []
    seen = set()

    for origin in raw_origins.split(","):
        origin = origin.strip().rstrip("/")

        if origin and origin not in seen:
            origins.append(origin)
            seen.add(origin)

    return origins


# Load local .env configuration.
_load_dotenv()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data"

PDF_DIR = Path(
    os.getenv(
        "PDF_FOLDER",
        str(DATA_DIR / "pdfs"),
    )
).resolve()

INDEX_DIR = Path(
    os.getenv(
        "INDEX_FOLDER",
        str(DATA_DIR / "index"),
    )
).resolve()

INDEX_FILE = INDEX_DIR / "index.json"


# ---------------------------------------------------------------------------
# AI model configuration
# ---------------------------------------------------------------------------

AI_API_KEY = os.getenv("AI_API_KEY", "").strip()

AI_MODEL = os.getenv(
    "AI_MODEL",
    "openai/gpt-oss-20b",
).strip()

AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    "https://api.groq.com/openai/v1",
).strip()

USE_LLM = bool(AI_API_KEY) and AI_API_KEY.lower() not in {
    "put_your_key_here",
    "changeme",
}

# gpt-oss is a REASONING model: it spends tokens thinking before it writes.
# With too small a budget the thinking consumes everything and the reply comes
# back empty (which silently degraded us to the extractive fallback). Keep the
# thinking short and leave plenty of room for the actual answer.
AI_MAX_TOKENS = _get_int("AI_MAX_TOKENS", default=1600, minimum=1)
AI_REASONING_EFFORT = os.getenv("AI_REASONING_EFFORT", "low").strip()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------

# How many retrieved pieces the AI may see at most. TOP_K is the MOST pieces we
# will ever send (see MIN_CONTEXT_PIECES / CONTEXT_MARGIN below for how many
# are usually sent). The system prompt tells the model to ignore pieces that do
# not address the question, so extra context does not make answers vaguer.
TOP_K = _get_int("TOP_K", default=8, minimum=1)
# Shown under each answer as "verified document sources". Raised alongside
# TOP_K so an answer that genuinely spans more pages can show them all.
MAX_CITATIONS = _get_int("MAX_CITATIONS", default=6, minimum=1)

# Adaptive context — the biggest lever on the Groq daily token limit.
# The AI's reply is small (~100 tokens); almost all of a request is the PDF
# pieces we send. Usually the best piece is a clear winner, so we send only the
# pieces scoring within CONTEXT_MARGIN of it, and never fewer than
# MIN_CONTEXT_PIECES. Close races still get up to TOP_K pieces. On 85 labeled
# questions this sends 3.5 pieces on average instead of 8 — about half the
# prompt tokens — while keeping nearly all of the right-section hits of fixed 8.
MIN_CONTEXT_PIECES = _get_int("MIN_CONTEXT_PIECES", default=3, minimum=1)
CONTEXT_MARGIN = _get_float("CONTEXT_MARGIN", default=0.25, minimum=0.0)

# Below this hybrid score we treat the top hit as "weak". We do not hard-refuse
# on a weak hit; we give a correlated best-effort answer and say it is related,
# not exact. We only hard-refuse when there is essentially nothing (see
# ai_answer.safety).
WEAK_SCORE = _get_float("WEAK_SCORE", default=0.14, minimum=0.0, maximum=1.0)
# Truly nothing relevant found -> refuse.
FLOOR_SCORE = _get_float("FLOOR_SCORE", default=0.045, minimum=0.0, maximum=1.0)

# Weight of the lexical (BM25) score vs the semantic (TF-IDF cosine) score when
# mixing the two rankers. 0 = semantic only, 1 = lexical only.
LEXICAL_WEIGHT = _get_float("LEXICAL_WEIGHT", default=0.5, minimum=0.0, maximum=1.0)


# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = _get_int("MAX_UPLOAD_MB", default=100, minimum=1)              # per single file
MAX_USER_STORAGE_MB = _get_int("MAX_USER_STORAGE_MB", default=100, minimum=1)  # per user total

# ---------------------------------------------------------------------------
# Per-user daily question limit
# ---------------------------------------------------------------------------
# Each user gets this many AI-written answers per day. It protects the shared
# Groq budget, so only questions the AI actually answers count: an answer
# served from the saved-answer cache, a greeting, or a refusal is free.
# The count resets at midnight in USAGE_TIMEZONE.
DAILY_QUESTION_LIMIT = _get_int("DAILY_QUESTION_LIMIT", default=30, minimum=1)
USAGE_TIMEZONE = os.getenv("USAGE_TIMEZONE", "Asia/Kolkata").strip()

# ---------------------------------------------------------------------------
# Shared (built-in) library + upload permissions
# ---------------------------------------------------------------------------
# PDFs stored under data/pdfs/<SHARED_OWNER>/ are the curated, verified drug
# labels that ship WITH the product. Every user can read and ask about them;
# nobody can delete them from the UI.
SHARED_OWNER = os.getenv("SHARED_OWNER", "shared").strip()

# Kept for compatibility only. Uploading is no longer gated on a permission
# flag: anyone may add a PDF, but only by supplying the official rxabbvie.com
# link it is published at (see backend/sources/rxabbvie.py).
ALLOW_USER_UPLOADS = os.getenv("ALLOW_USER_UPLOADS", "false").strip().lower() in {"1", "true", "yes"}

# Protects DELETING a medicine from the shared built-in library.
# Change it in .env for a real deploy.
ADMIN_KEY = os.getenv("ADMIN_KEY", "medcite-admin").strip()


# Section-aware ranking (see search/hybrid.py). US drug labels share one fixed
# section structure (4 Contraindications, 6 Adverse Reactions, 10 Overdosage...),
# so a question's intent says which section should answer it. These are added
# to the 0-1 blended score.
SECTION_BOOST = _get_float("SECTION_BOOST", default=0.35, minimum=0.0)            # heading fits intent
HEADING_TERM_BOOST = _get_float("HEADING_TERM_BOOST", default=0.15, minimum=0.0)  # query word in heading
# Page-1 Highlights and 17 Patient Counseling repeat every topic in summary
# form, so they outrank the full section on raw word overlap. When a specific
# section is wanted, nudge these summaries down so the detailed section wins.
SUMMARY_PENALTY = _get_float("SUMMARY_PENALTY", default=0.12, minimum=0.0)

# ---------------------------------------------------------------------------
# CORS (the React dev server runs on :3000, preview builds on :8000)
#
# Vite falls back to the next free port when 3000 is taken, so a second dev
# server lands on 3001/3002. Those must be allowed too: otherwise the browser
# silently drops every API response (the request still reaches the server) and
# the UI sits on "connecting…" with an empty medicine library. A deployed app
# serves the page and the API from the same origin, so it needs no entry here.
# ---------------------------------------------------------------------------
_DEV_PORTS = ("3000", "3001", "3002", "5173", "8000")
ALLOWED_ORIGINS = _get_origins(
    ",".join(f"http://{host}:{port}"
             for host in ("localhost", "127.0.0.1")
             for port in _DEV_PORTS)
)
