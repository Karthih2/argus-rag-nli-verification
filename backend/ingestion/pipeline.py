"""Ingest one document: register -> parse -> chunk -> embed -> store -> wait until searchable."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.db.client import chunks, documents, get_fs
from backend.ingestion.chunking import chunk_elements
from backend.ingestion.intake import register_upload
from backend.ingestion.report import build_report
from backend.retrieval.atlas_search import wait_until_searchable
from backend.retrieval.embedder import embed_for_storage

log = logging.getLogger(__name__)


def ingest_document(
    file_path: Path,
    dataset_id: str,
    file_name: str | None = None,
) -> dict | None:
    """Ingest one document into a dataset. Returns the document record, or None if duplicate."""
    file_name = file_name or file_path.name
    data = file_path.read_bytes()
    doc = register_upload(data, file_name, dataset_id)
    if doc is None:
        return None
    try:
        _process(doc, file_path)
    except Exception as e:
        log.exception("Ingestion failed for %s", file_name)
        chunks().delete_many({"document_id": doc["_id"]})
        # On failed ingest, delete GridFS file
        gridfs_id = doc.get("file", {}).get("gridfs_id")
        if gridfs_id:
            try:
                from bson import ObjectId
                get_fs().delete(ObjectId(gridfs_id))
            except (ImportError, OSError, ValueError):
                log.warning("Could not delete GridFS file %s", gridfs_id)
        _set(doc["_id"], {"processing.status": "failed", "processing.error": str(e)})
        raise
    return documents().find_one({"_id": doc["_id"]})


def _process(doc: dict, file_path: Path) -> None:
    doc_id, dataset_id = doc["_id"], doc["dataset_id"]
    _set(doc_id, {"processing.status": "parsing"})
    result = _parse(file_path)
    title = result.metadata.get("title") or Path(doc["file"]["name"]).stem
    pages = result.metadata.get("page_count", 0)
    _set(doc_id, {"metadata.title": title, "outline": result.outline, "processing.pages_done": pages})

    _set(doc_id, {"processing.status": "embedding"})
    records = chunk_elements(result.elements, doc_id, title)
    for r, vector in zip(records, embed_for_storage([r["embed_text"] for r in records])):
        r.update(
            dataset_id=dataset_id,
            document_id=doc_id,
            file_name=doc["file"]["name"],
            doc_title=title,
            embedding=vector,
        )
    if not documents().find_one({"_id": doc_id}, {"_id": 1}):
        raise RuntimeError("document was deleted during ingestion")
    if records:
        chunks().insert_many(records, ordered=False)

    _set(doc_id, {"processing.status": "indexing"})
    stats = build_report(result, records)
    if records and not wait_until_searchable(dataset_id, doc_id):
        # Leave as 'indexing' and let next status poll retry, don't delete finished chunks
        log.warning("Atlas search index timeout for %s — leaving as 'indexing'", doc["file"]["name"])
        _set(doc_id, {"stats": stats})
        return
    _set(
        doc_id,
        {
            "processing.status": "ready",
            "stats": stats,
            "pages": [{"n": p.n, "kind": p.kind, "chunks": p.chunks} for p in result.pages],
            "ready_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    log.info(
        "Ready: %s | %d chunks, %d tables",
        doc["file"]["name"],
        stats["chunks"],
        stats.get("tables", 0),
    )


def _parse(file_path: Path):
    """Parse with Docling. Only PDF supported via Docling parser."""
    from backend.ingestion.parse_docling import parse_docling
    return parse_docling(file_path)


def _set(doc_id: str, fields: dict) -> None:
    documents().update_one({"_id": doc_id}, {"$set": fields})
