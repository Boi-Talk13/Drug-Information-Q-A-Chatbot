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


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------

TOP_K = _get_int(
    "TOP_K",
    default=5,
    minimum=1,
)

MAX_CITATIONS = _get_int(
    "MAX_CITATIONS",
    default=4,
    minimum=1,
)

WEAK_SCORE = _get_float(
    "WEAK_SCORE",
    default=0.14,
    minimum=0.0,
    maximum=1.0,
)

FLOOR_SCORE = _get_float(
    "FLOOR_SCORE",
    default=0.045,
    minimum=0.0,
    maximum=1.0,
)

LEXICAL_WEIGHT = _get_float(
    "LEXICAL_WEIGHT",
    default=0.5,
    minimum=0.0,
    maximum=1.0,
)


# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = _get_int(
    "MAX_UPLOAD_MB",
    default=100,
    minimum=1,
)

MAX_USER_STORAGE_MB = _get_int(
    "MAX_USER_STORAGE_MB",
    default=100,
    minimum=1,
)


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------

DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000,"
    "http://localhost:8000,"
    "http://127.0.0.1:3000,"
    "http://127.0.0.1:8000"
)

ALLOWED_ORIGINS = _get_origins(
    DEFAULT_ALLOWED_ORIGINS
)