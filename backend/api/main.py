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

from fastapi import FastAPI, File, HTTPException, UploadFile
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
    if not config.INDEX_FILE.exists():
        try:
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
def drugs() -> dict:
    r = get_retriever()
    return {"drugs": list(r.documents.values())}


@app.get("/api/pdf/{drug_id}")
def get_pdf(drug_id: str) -> FileResponse:
    """Serve the raw PDF for a drug so the frontend can render the real pages."""
    r = get_retriever()
    doc = r.document(drug_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No PDF for this drug")
    path = config.PDF_DIR / doc["filename"]
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
    start = time.perf_counter()
    result = answer_question(
        question=req.question,
        history=[t.model_dump() for t in req.history],
        drug_filter=req.drug_filter,
        retriever=r,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    uid = req.user_id or "anonymous"
    # Per-user records: the user_id keeps each person's data separate.
    db.log_answer(req.question, req.drug_filter, result, latency_ms, user_id=uid)
    db.save_chat(uid, req.drug_filter, req.question, result)
    return result


@app.get("/api/stats")
def stats(user_id: Optional[str] = None) -> dict:
    """Monitoring numbers. Pass ?user_id= to scope to one user."""
    return db.stats(user_id)


@app.get("/api/history/{user_id}")
def history(user_id: str, limit: int = 50) -> dict:
    """Return one user's saved chat history (row-level isolated by user_id)."""
    return {"user_id": user_id, "history": db.get_history(user_id, limit)}


@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)) -> dict:
    """Upload one or more PDFs. Each file is parsed on its own (fast) and merged
    into the index; the retriever is refreshed once at the end."""
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue
        dest = config.PDF_DIR / file.filename
        dest.write_bytes(await file.read())
        meta = add_or_replace_pdf(dest)          # parse only this file
        saved.append({
            "id": meta["drug_id"],
            "name": meta["title"],
            "pages": meta["pages"],
            "num_chunks": meta["num_chunks"],
        })

    if not saved:
        raise HTTPException(status_code=400, detail="Please upload .pdf files")

    refresh_retriever()
    # Backward compatible: single-file callers read the top-level fields too.
    return {**saved[0], "uploaded": saved, "count": len(saved)}


@app.delete("/api/drugs/{drug_id}")
def delete_drug(drug_id: str) -> dict:
    """Delete a medicine: remove it from the index and delete its PDF file."""
    r = get_retriever()
    doc = r.document(drug_id)
    removed = remove_drug(drug_id)
    if doc:
        pdf_path = config.PDF_DIR / doc["filename"]
        try:
            pdf_path.unlink(missing_ok=True)
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
