"""
Central configuration for the MedCite backend.

Everything is read from environment variables (see .env.example) with safe
defaults so the whole system runs on a laptop with zero setup. Nothing here is
secret; the real secret (AI_API_KEY) is only ever read from the environment.
"""
from __future__ import annotations

import os
from pathlib import Path

# backend/config.py  ->  backend/  ->  project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load .env from the project root, if present, so a local `uvicorn` run picks
# up AI_API_KEY without any extra step. python-dotenv is optional; if it isn't
# installed we fall back to a tiny hand parser. Real environment variables
# always win over the file.
# ---------------------------------------------------------------------------
def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except Exception:
        pass
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = Path(os.getenv("PDF_FOLDER", str(DATA_DIR / "pdfs"))).resolve()
INDEX_DIR = Path(os.getenv("INDEX_FOLDER", str(DATA_DIR / "index"))).resolve()

# The built search index lives here as plain, inspectable JSON.
INDEX_FILE = INDEX_DIR / "index.json"

# ---------------------------------------------------------------------------
# AI model (Groq, optional)
# ---------------------------------------------------------------------------
# If no key is set the backend still works: it falls back to an extractive
# answer built directly from the retrieved PDF text, which keeps every page
# number provably correct.
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# Database — PostgreSQL when DATABASE_URL is set, else a local SQLite fallback.
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-20b").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1").strip()
USE_LLM = bool(AI_API_KEY) and AI_API_KEY.lower() not in {"put_your_key_here", "changeme"}

# ---------------------------------------------------------------------------
# Retrieval tuning
# ---------------------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "5"))            # pieces sent to the AI
MAX_CITATIONS = int(os.getenv("MAX_CITATIONS", "4"))

# ---------------------------------------------------------------------------
# Upload limits — keep storage (and cloud cost) bounded.
# ---------------------------------------------------------------------------
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))          # per single file
MAX_USER_STORAGE_MB = int(os.getenv("MAX_USER_STORAGE_MB", "100"))  # per user total

# Below this hybrid score we treat the top hit as "weak". We do not hard-refuse
# on a weak hit; we give a correlated best-effort answer and say it is related,
# not exact. We only hard-refuse when there is essentially nothing (see
# ai_answer.safety).
WEAK_SCORE = float(os.getenv("WEAK_SCORE", "0.14"))
# Truly nothing relevant found -> refuse.
FLOOR_SCORE = float(os.getenv("FLOOR_SCORE", "0.045"))

# Weight of the lexical (BM25) score vs the semantic (TF-IDF cosine) score when
# mixing the two rankers. 0 = semantic only, 1 = lexical only.
LEXICAL_WEIGHT = float(os.getenv("LEXICAL_WEIGHT", "0.5"))

# ---------------------------------------------------------------------------
# CORS (the React dev server runs on :3000, preview builds on :8000)
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000",
).split(",")
