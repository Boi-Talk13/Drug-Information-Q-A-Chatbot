"""
FastAPI app for MedCite.

Endpoints (matching what the React frontend calls):
  POST /api/chat    {question, history, drug_filter} -> answer + citations
  POST /api/upload  multipart file=<pdf>             -> {id, name, pages}
  GET  /api/drugs                                     -> indexed medicines
  GET  /api/health                                    -> status + mode

The retriever is loaded once and cached. Uploading a new PDF rebuilds the index
and refreshes the cache, so a new medicine works straight away.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import config
from ..ai_answer.answer import answer_question
from ..pdf_reader.reader import drug_id_from_filename
from ..search.hybrid import Retriever
from ..search.index import add_or_replace_pdf, build_index, remove_drug
from . import db

app = FastAPI(title="MedCite API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- cached retriever -------------------------------------------------------
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def refresh_retriever() -> Retriever:
    global _retriever
    _retriever = Retriever()
    return _retriever


@app.on_event("startup")
def _startup() -> None:
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    # Build the index on boot if PDFs exist but no index has been built yet.
    # Build on first boot, or migrate an old (pre-owner) index to the new format.
    try:
        import json as _json
        needs_build = not config.INDEX_FILE.exists()
        if not needs_build:
            data = _json.loads(config.INDEX_FILE.read_text())
            needs_build = data.get("version", 1) < 2
        if needs_build:
            build_index()
    except Exception:
        pass
    get_retriever()


# --- request/response models -----------------------------------------------
class HistoryTurn(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    question: str
    history: List[HistoryTurn] = []
    drug_filter: Optional[str] = None
    user_id: Optional[str] = None


class UserRequest(BaseModel):
    token: str


# --- endpoints --------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    r = get_retriever()
    return {
        "status": "ok",
        "mode": "groq" if config.USE_LLM else "extractive",
        "model": config.AI_MODEL if config.USE_LLM else None,
        "database": db.backend_name(),
        "indexed_drugs": list(r.documents.keys()),
        "num_chunks": len(r.chunks),
    }


@app.get("/api/drugs")
def drugs(user_id: str = "anonymous") -> dict:
    """Only this user's own uploaded PDFs (fully private libraries)."""
    r = get_retriever()
    return {"drugs": r.documents_for(user_id)}


@app.get("/api/pdf/{drug_id}")
def get_pdf(drug_id: str, user_id: str = "anonymous") -> FileResponse:
    """Serve the raw PDF — only if it belongs to this user."""
    r = get_retriever()
    doc = r.document(drug_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No PDF for this drug")
    path = config.PDF_DIR / user_id / doc["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'},
    )


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    r = get_retriever()
    uid = req.user_id or "anonymous"

    # Same self-contained question again -> return the saved answer (consistent
    # and instant, no repeated Groq call). Short follow-ups depend on the chat
    # context, so we don't cache those.
    cacheable = len(req.question.split()) >= 4
    if cacheable:
        cached = db.get_cached_answer(uid, req.drug_filter, req.question)
        if cached:
            db.log_answer(req.question, req.drug_filter, cached, 0, user_id=uid)
            return cached

    start = time.perf_counter()
    result = answer_question(
        question=req.question,
        history=[t.model_dump() for t in req.history],
        drug_filter=req.drug_filter,
        retriever=r,
        user_id=uid,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    # Per-user records: the user_id keeps each person's data separate.
    db.log_answer(req.question, req.drug_filter, result, latency_ms, user_id=uid)
    db.save_chat(uid, req.drug_filter, req.question, result)
    if cacheable and not result.get("is_refusal"):
        db.cache_answer(uid, req.drug_filter, req.question, result)
    return result


@app.get("/api/stats")
def stats(user_id: Optional[str] = None) -> dict:
    """Monitoring numbers. Pass ?user_id= to scope to one user."""
    return db.stats(user_id)


@app.post("/api/user")
def register_user(req: UserRequest) -> dict:
    """Turn a per-browser token into a short id like user-101 (assigned once)."""
    return {"user_id": db.resolve_user(req.token)}


@app.get("/api/history/{user_id}")
def history(user_id: str, limit: int = 50) -> dict:
    """Return one user's saved chat history, grouped by day (Today/Yesterday)."""
    return {"user_id": user_id, "history": db.get_history(user_id, limit),
            "by_day": db.get_history_by_day(user_id, limit)}


@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...), user_id: str = Form("anonymous")) -> dict:
    """Upload one or more PDFs into THIS user's private library. Each file is
    parsed on its own (fast) and stored under data/pdfs/<user_id>/."""
    owner_dir = config.PDF_DIR / user_id
    owner_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    max_total = config.MAX_USER_STORAGE_MB * 1024 * 1024
    used = sum(f.stat().st_size for f in owner_dir.glob("*.pdf"))

    saved = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue
        data = await file.read()
        size = len(data)
        # 1) per-file limit
        if size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f'"{file.filename}" is {size // (1024*1024)} MB — over the '
                       f'{config.MAX_UPLOAD_MB} MB per-file limit.')
        # 2) per-user total-storage limit (skip re-counting a file being replaced)
        existing = (owner_dir / Path(file.filename).name)
        replacing = existing.stat().st_size if existing.exists() else 0
        if used - replacing + size > max_total:
            raise HTTPException(
                status_code=413,
                detail=f'Upload would exceed your {config.MAX_USER_STORAGE_MB} MB storage '
                       f'limit. Delete some PDFs first.')
        used = used - replacing + size

        dest = owner_dir / Path(file.filename).name
        dest.write_bytes(data)
        meta = add_or_replace_pdf(dest, owner=user_id)     # parse only this file
        saved.append({
            "id": meta["drug_id"],
            "name": meta["title"],
            "pages": meta["pages"],
            "num_chunks": meta["num_chunks"],
        })

    if not saved:
        raise HTTPException(status_code=400, detail="Please upload .pdf files")

    refresh_retriever()
    return {**saved[0], "uploaded": saved, "count": len(saved)}


@app.delete("/api/drugs/{drug_id}")
def delete_drug(drug_id: str, user_id: str = "anonymous") -> dict:
    """Delete one of THIS user's medicines (index entry + their PDF file)."""
    r = get_retriever()
    doc = r.document(drug_id, user_id)
    removed = remove_drug(drug_id, owner=user_id)
    if doc:
        try:
            (config.PDF_DIR / user_id / doc["filename"]).unlink(missing_ok=True)
        except Exception:
            pass
    refresh_retriever()
    if not removed:
        raise HTTPException(status_code=404, detail="No such medicine")
    return {"deleted": drug_id, "ok": True}


# --- serve the built frontend (optional) ------------------------------------
# If the React app has been built (frontend/dist), serve it on the same origin
# so http://localhost:8000 shows the whole app, exactly as the README promises.
# Mounted last so it never shadows the /api routes above.
_FRONTEND_DIST = config.PROJECT_ROOT / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
