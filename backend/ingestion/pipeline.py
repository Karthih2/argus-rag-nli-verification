"""Ingest one PDF: register -> parse -> chunk -> embed -> store -> wait until searchable."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.db.client import chunks, documents
from backend.ingestion.chunking import chunk_elements
from backend.ingestion.intake import register_upload
from backend.ingestion.report import build_report
from backend.library import delete_gridfs_file
from backend.retrieval.atlas_search import is_searchable, wait_until_searchable
from backend.retrieval.embedder import embed_for_storage

log = logging.getLogger(__name__)


def ingest_document(file_path: Path, dataset_id: str, file_name: str | None = None) -> dict | None:
    """Ingest one PDF into a dataset. Returns the document record, or None if it is a duplicate."""
    file_name = file_name or file_path.name
    doc = register_upload(file_path.read_bytes(), file_name, dataset_id)
    if doc is None:
        return None
    try:
        _process(doc, file_path)
    except Exception as e:
        log.exception("Ingestion failed for %s", file_name)
        chunks().delete_many({"document_id": doc["_id"]})
        delete_gridfs_file(doc["file"]["gridfs_id"])
        _set(doc["_id"], {"processing.status": "failed", "processing.error": str(e)})
        raise
    return documents().find_one({"_id": doc["_id"]})


def refresh_indexing(doc: dict) -> dict:
    """A document left in 'indexing' (index wait timed out) becomes 'ready' once search finds it.

    Called when the document is read, so a status poll from the UI finishes the job.
    """
    if doc.get("processing", {}).get("status") == "indexing" and is_searchable(doc["dataset_id"], doc["_id"]):
        _mark_ready(doc["_id"])
        doc = documents().find_one({"_id": doc["_id"]})
    return doc


def _process(doc: dict, file_path: Path) -> None:
    doc_id, dataset_id = doc["_id"], doc["dataset_id"]
    from backend.ingestion.parse_docling import parse_docling  # heavy; load only when ingesting

    _set(doc_id, {"processing.status": "parsing"})
    result = parse_docling(file_path)
    title = result.metadata.get("title") or Path(doc["file"]["name"]).stem
    _set(doc_id, {"metadata.title": title, "outline": result.outline,
                  "processing.pages_done": result.metadata.get("page_count", 0)})

    _set(doc_id, {"processing.status": "embedding"})
    records = chunk_elements(result.elements, doc_id, title)
    for r, vector in zip(records, embed_for_storage([r["embed_text"] for r in records])):
        r.update(dataset_id=dataset_id, document_id=doc_id, file_name=doc["file"]["name"],
                 doc_title=title, embedding=vector)
    if not documents().find_one({"_id": doc_id}, {"_id": 1}):
        raise RuntimeError("document was deleted during ingestion")
    if records:
        chunks().insert_many(records, ordered=False)

    stats = build_report(result, records)
    pages = [{"n": p.n, "kind": p.kind, "chunks": p.chunks} for p in result.pages]
    _set(doc_id, {"processing.status": "indexing", "stats": stats, "pages": pages})
    if records and not wait_until_searchable(dataset_id, doc_id):
        log.warning("Search index not ready for %s yet; it becomes ready on a later status check",
                    doc["file"]["name"])
        return
    _mark_ready(doc_id)
    log.info("Ready: %s | %d chunks, %d tables", doc["file"]["name"], stats["chunks"], stats.get("tables", 0))


def _mark_ready(doc_id: str) -> None:
    _set(doc_id, {"processing.status": "ready", "ready_at": datetime.now(timezone.utc).isoformat()})


def _set(doc_id: str, fields: dict) -> None:
    documents().update_one({"_id": doc_id}, {"$set": fields})
