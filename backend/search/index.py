"""
Build and load the search index.

The index is plain JSON on disk (data/index/index.json). It is easy to inspect,
easy to diff, and every chunk in it carries its drug, section and page number,
so a search result always comes back with a correct page.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from .. import config
from ..pdf_reader.chunker import Chunk, chunk_document
from ..pdf_reader.reader import read_pdf


def build_index(pdf_dir: Path | None = None, index_file: Path | None = None) -> Dict:
    """Read every PDF in `pdf_dir`, chunk it, and write the index to disk."""
    pdf_dir = Path(pdf_dir or config.PDF_DIR)
    index_file = Path(index_file or config.INDEX_FILE)
    index_file.parent.mkdir(parents=True, exist_ok=True)

    chunks: List[Chunk] = []
    documents: Dict[str, Dict] = {}

    pdf_paths = sorted(p for p in pdf_dir.glob("*.pdf")) + sorted(pdf_dir.glob("*.PDF"))
    for path in pdf_paths:
        doc = read_pdf(path)
        doc_chunks = chunk_document(doc)
        chunks.extend(doc_chunks)
        documents[doc.drug_id] = {
            "drug_id": doc.drug_id,
            "filename": doc.filename,
            "title": doc.title,
            "pages": doc.num_pages,
            "num_chunks": len(doc_chunks),
        }

    index = {
        "version": 1,
        "documents": documents,
        "chunks": [asdict(c) for c in chunks],
    }
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2))
    return index


def load_index(index_file: Path | None = None) -> Dict:
    index_file = Path(index_file or config.INDEX_FILE)
    if not index_file.exists():
        return {"version": 1, "documents": {}, "chunks": []}
    return json.loads(index_file.read_text())


def _save(index: Dict, index_file: Path) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2))


def add_or_replace_pdf(path: Path | str, index_file: Path | None = None) -> Dict:
    """Parse ONE pdf and merge it into the existing index.

    This is what makes uploads fast: we only read the new file, not every PDF
    already indexed. If a document with the same drug id exists, it is replaced.
    """
    path = Path(path)
    index_file = Path(index_file or config.INDEX_FILE)
    index = load_index(index_file)

    doc = read_pdf(path)
    doc_chunks = chunk_document(doc)

    # Drop any previous chunks/doc for this drug id, then add the fresh ones.
    index["chunks"] = [c for c in index["chunks"] if c.get("drug_id") != doc.drug_id]
    index["chunks"].extend(asdict(c) for c in doc_chunks)
    index.setdefault("documents", {})[doc.drug_id] = {
        "drug_id": doc.drug_id,
        "filename": doc.filename,
        "title": doc.title,
        "pages": doc.num_pages,
        "num_chunks": len(doc_chunks),
    }
    _save(index, index_file)
    return index["documents"][doc.drug_id]


def remove_drug(drug_id: str, index_file: Path | None = None) -> bool:
    """Remove a drug's document and chunks from the index. Returns True if found."""
    index_file = Path(index_file or config.INDEX_FILE)
    index = load_index(index_file)
    if drug_id not in index.get("documents", {}):
        return False
    del index["documents"][drug_id]
    index["chunks"] = [c for c in index["chunks"] if c.get("drug_id") != drug_id]
    _save(index, index_file)
    return True
