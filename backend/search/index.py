"""
Build and load the search index.

The index is plain JSON on disk (data/index/index.json). Every chunk carries its
drug, section, page number — and its **owner** (the user_id who uploaded it), so
each user only ever sees and searches their OWN PDFs (fully private libraries).

On disk, PDFs are stored per owner: data/pdfs/<owner>/<filename> — so two users
uploading a file with the same name never collide.

Documents are keyed internally by "<owner>::<drug_id>"; within one owner the
drug_id is unique, and across owners the same drug_id can coexist independently.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from .. import config
from ..pdf_reader.chunker import Chunk, chunk_document
from ..pdf_reader.reader import read_pdf


def _key(owner: str, drug_id: str) -> str:
    return f"{owner}::{drug_id}"


def _doc_entry(owner: str, doc, num_chunks: int) -> Dict:
    return {
        "owner": owner,
        "drug_id": doc.drug_id,
        "filename": doc.filename,
        "title": doc.title,
        "pages": doc.num_pages,
        "num_chunks": num_chunks,
    }


def _chunks_as_dicts(doc_chunks: List[Chunk], owner: str) -> List[Dict]:
    out = []
    for c in doc_chunks:
        d = asdict(c)
        d["owner"] = owner
        out.append(d)
    return out


def build_index(pdf_dir: Path | None = None, index_file: Path | None = None) -> Dict:
    """Read every PDF under data/pdfs/<owner>/ and (re)build the whole index.

    Each PDF's owner is the sub-folder it sits in. Flat PDFs directly under
    data/pdfs (no owner folder) are ignored in the per-user model.
    """
    pdf_dir = Path(pdf_dir or config.PDF_DIR)
    index_file = Path(index_file or config.INDEX_FILE)
    index_file.parent.mkdir(parents=True, exist_ok=True)

    chunks: List[Dict] = []
    documents: Dict[str, Dict] = {}

    for owner_dir in sorted(p for p in pdf_dir.iterdir() if p.is_dir()):
        owner = owner_dir.name
        pdf_paths = sorted(owner_dir.glob("*.pdf")) + sorted(owner_dir.glob("*.PDF"))
        for path in pdf_paths:
            doc = read_pdf(path)
            doc_chunks = chunk_document(doc)
            chunks.extend(_chunks_as_dicts(doc_chunks, owner))
            documents[_key(owner, doc.drug_id)] = _doc_entry(owner, doc, len(doc_chunks))

    index = {"version": 2, "documents": documents, "chunks": chunks}
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2))
    return index


def load_index(index_file: Path | None = None) -> Dict:
    index_file = Path(index_file or config.INDEX_FILE)
    if not index_file.exists():
        return {"version": 2, "documents": {}, "chunks": []}
    return json.loads(index_file.read_text())


def _save(index: Dict, index_file: Path) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2))


def add_or_replace_pdf(path: Path | str, owner: str, index_file: Path | None = None) -> Dict:
    """Parse ONE pdf (owned by `owner`) and merge it into the index.

    Only this file is read (fast). Any previous doc with the same owner+drug_id
    is replaced. Other users' documents are untouched.
    """
    path = Path(path)
    index_file = Path(index_file or config.INDEX_FILE)
    index = load_index(index_file)

    doc = read_pdf(path)
    doc_chunks = chunk_document(doc)

    # Drop this owner's previous chunks for this drug id, keep everyone else's.
    index["chunks"] = [
        c for c in index["chunks"]
        if not (c.get("owner") == owner and c.get("drug_id") == doc.drug_id)
    ]
    index["chunks"].extend(_chunks_as_dicts(doc_chunks, owner))
    index.setdefault("documents", {})[_key(owner, doc.drug_id)] = _doc_entry(owner, doc, len(doc_chunks))
    _save(index, index_file)
    return index["documents"][_key(owner, doc.drug_id)]


def remove_drug(drug_id: str, owner: str, index_file: Path | None = None) -> bool:
    """Remove one owner's drug (document + chunks). Returns True if found."""
    index_file = Path(index_file or config.INDEX_FILE)
    index = load_index(index_file)
    k = _key(owner, drug_id)
    if k not in index.get("documents", {}):
        return False
    del index["documents"][k]
    index["chunks"] = [
        c for c in index["chunks"]
        if not (c.get("owner") == owner and c.get("drug_id") == drug_id)
    ]
    _save(index, index_file)
    return True
