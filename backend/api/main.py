"""
FastAPI app for MedCite.

Endpoints (matching what the React frontend calls):
  POST /api/chat    {question, history, drug_filter} -> answer + citations
  POST /api/upload  multipart file=<pdf>             -> {id, name, pages}
  GET  /api/drugs                                     -> indexed medicines
  GET  /api/health                                    -> status + mode
  GET  /api/usage   ?user_id=                         -> today's questions left

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
from ..ai_answer import safety
from ..ai_answer.answer import answer_question
from ..pdf_reader.reader import drug_id_from_filename, read_pdf
from ..pdf_reader.validator import looks_like_drug_label
from ..sources.rxabbvie import catalog_size, verify_upload
from ..search.hybrid import Retriever
from ..search.index import add_or_replace_pdf_doc, build_index, remove_drug
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
    """Return the shared search retriever, building it on first use."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def refresh_retriever() -> Retriever:
    """Rebuild the retriever so a changed index (e.g. after an upload) is searched."""
    global _retriever
    _retriever = Retriever()
    return _retriever


@app.on_event("startup")
def _startup() -> None:
    """Create the data folders and build the search index on first boot or after an index format change."""
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
    """One earlier chat turn sent with a question, used to understand follow-ups."""
    role: str
    text: str


class ChatRequest(BaseModel):
    """Body of POST /api/chat."""
    question: str
    history: List[HistoryTurn] = []
    drug_filter: Optional[str] = None
    user_id: Optional[str] = None


class UserRequest(BaseModel):
    """Body of POST /api/user: the browser's random token."""
    token: str


# --- endpoints --------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    """Status check: answer mode, model, database, and what is indexed."""
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
    """The shared built-in library (visible to everyone) plus this user's own
    uploads. Another user's private PDFs are never included."""
    r = get_retriever()
    docs = r.documents_for(user_id)
    return {
        "drugs": [{**d, "shared": d.get("owner") == config.SHARED_OWNER} for d in docs],
        # Uploading is open to everyone, but only for a PDF whose official
        # RxAbbVie link the user can supply. The UI uses this to explain the
        # rule; the real enforcement is in /api/upload.
        "uploads_open": True,
        "source_host": "www.rxabbvie.com",
        "source_catalog_size": catalog_size(),
    }


@app.get("/api/pdf/{drug_id}")
def get_pdf(drug_id: str, user_id: str = "anonymous") -> FileResponse:
    """Serve the raw PDF — from the shared library, or this user's own upload."""
    r = get_retriever()
    doc = r.document(drug_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No PDF for this drug")
    # Read it from whichever library it actually lives in.
    path = config.PDF_DIR / doc.get("owner", user_id) / doc["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'},
    )


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    """Answer one question: serve a saved answer if there is one, otherwise run the full pipeline within the daily limit."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    r = get_retriever()
    uid = req.user_id or "anonymous"
    history = [t.model_dump() for t in req.history]

    # Saved answers. A question asked before is answered from the database:
    # instant, no Groq call, and it does not count toward the daily limit.
    #  * Built-in (shared) medicines: everyone reads the same PDF, so one saved
    #    answer serves EVERY user who asks the same question.
    #  * A user's own uploaded PDF: its saved answers stay private to them.
    #  * Follow-ups ("and for children?") depend on the earlier chat, and very
    #    short questions are too vague, so neither is served from the cache.
    doc = r.document(req.drug_filter, uid) if req.drug_filter else None
    shared = bool(doc) and doc.get("owner") == config.SHARED_OWNER
    cache_scope = config.SHARED_OWNER if shared else uid
    is_followup = safety.rewrite_followup(req.question, history) != req.question
    cacheable = len(req.question.split()) >= 4 and not is_followup
    if cacheable:
        cached = db.get_cached_answer(cache_scope, req.drug_filter, req.question)
        if cached:
            cached = {**cached, "from_cache": True}
            db.log_answer(req.question, req.drug_filter, cached, 0, user_id=uid)
            db.save_chat(uid, req.drug_filter, req.question, cached)
            return {**cached, "usage": _usage(uid)}

    # Daily limit: reserve one AI answer up front, and give it back if the AI
    # ends up not being used (greeting, refusal, or the backup writer).
    reserved = db.reserve_ai_answer(uid, config.DAILY_QUESTION_LIMIT)

    start = time.perf_counter()
    result = answer_question(
        question=req.question,
        history=history,
        drug_filter=req.drug_filter,
        retriever=r,
        user_id=uid,
        llm_allowed=reserved,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if reserved and result.get("answer_mode") != "llm":
        db.release_ai_answer(uid)

    # Per-user records: the user_id keeps each person's data separate.
    db.log_answer(req.question, req.drug_filter, result, latency_ms, user_id=uid)
    db.save_chat(uid, req.drug_filter, req.question, result)
    # Only cache answers the AI wrote. A backup-writer answer saved here would
    # keep being served to everyone long after the AI is available again.
    if cacheable and not result.get("is_refusal") and result.get("answer_mode") == "llm":
        db.cache_answer(cache_scope, req.drug_filter, req.question, result)
    return {**result, "usage": _usage(uid)}


def _usage(uid: str) -> dict:
    """Today's AI-answer allowance for one user."""
    used = db.usage_today(uid)
    limit = config.DAILY_QUESTION_LIMIT
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


@app.get("/api/usage")
def usage(user_id: str = "anonymous") -> dict:
    """How many of today's questions this user has left."""
    return _usage(user_id)


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
async def upload(
    files: List[UploadFile] = File(...),
    user_id: str = Form("anonymous"),
    source_url: str = Form(""),
) -> dict:
    """Add a drug-label PDF, verified against its official RxAbbVie source.

    The library is not open to arbitrary files. Every upload passes four gates:
      1. SOURCE  — the pasted link is on rxabbvie.com (see sources/rxabbvie.py).
      2. CATALOG — it names one of the PDFs actually published on that site.
      3. NAME    — the chosen file matches the file the link names, so a valid
                   link cannot be used to bring in some other document.
      4. CONTENT — the file still has to parse as prescribing information, or it
                   is rejected and deleted (see validator.py).

    One link identifies one PDF, so exactly one file may be uploaded at a time.
    """
    if len(files) > 1:
        raise HTTPException(
            status_code=400,
            detail="Upload one PDF at a time — each file needs its own RxAbbVie link.")

    owner = user_id
    owner_dir = config.PDF_DIR / owner
    owner_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    max_total = config.MAX_USER_STORAGE_MB * 1024 * 1024
    used = sum(f.stat().st_size for f in owner_dir.glob("*.pdf"))

    saved = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue

        # Gates 1-3: the link must be a real RxAbbVie PDF and must name THIS
        # file. Checked before anything is written to disk.
        ok, why, _ = verify_upload(source_url, file.filename)
        if not ok:
            raise HTTPException(status_code=403, detail=why)

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

        # Parse once, then confirm this is really a medicine's prescribing
        # information before it's added to the user's library — rejects
        # resumes, invoices, or any unrelated PDF with a clear reason why.
        parsed = read_pdf(dest)
        is_valid, reason = looks_like_drug_label(parsed)
        if not is_valid:
            dest.unlink(missing_ok=True)
            raise HTTPException(
                status_code=422,
                detail=f'"{file.filename}" was not added. {reason}')

        meta = add_or_replace_pdf_doc(parsed, owner=owner)   # no re-parsing
        meta["source_url"] = source_url.strip()
        saved.append({
            "id": meta["drug_id"],
            "name": meta["title"],
            "pages": meta["pages"],
            "num_chunks": meta["num_chunks"],
            "shared": owner == config.SHARED_OWNER,
        })

    if not saved:
        raise HTTPException(status_code=400, detail="Please upload .pdf files")

    refresh_retriever()
    return {**saved[0], "uploaded": saved, "count": len(saved)}


@app.delete("/api/drugs/{drug_id}")
def delete_drug(drug_id: str, user_id: str = "anonymous", admin_key: str = "") -> dict:
    """Delete a medicine. A user can only delete their OWN upload — the shared
    built-in library is read-only unless the admin key is supplied."""
    r = get_retriever()
    doc = r.document(drug_id, user_id)
    if doc and doc.get("owner") == config.SHARED_OWNER:
        if admin_key != config.ADMIN_KEY:
            raise HTTPException(
                status_code=403,
                detail="This medicine is part of the shared built-in library and "
                       "cannot be deleted.")
        owner = config.SHARED_OWNER
    else:
        owner = user_id

    removed = remove_drug(drug_id, owner=owner)
    if doc:
        try:
            (config.PDF_DIR / owner / doc["filename"]).unlink(missing_ok=True)
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
