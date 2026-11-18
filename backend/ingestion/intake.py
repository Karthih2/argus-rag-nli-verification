"""Upload intake: PDF only, size/page limits, hash, deduplicate, store the original in GridFS."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium

from backend.common.ids import file_sha256, make_id
from backend.config import settings
from backend.db.client import documents, get_fs

log = logging.getLogger(__name__)


class IntakeError(ValueError):
    """The upload breaks a limit (type, size, pages) or isn't a readable PDF."""


def check_upload(data: bytes, file_name: str) -> int:
    """Raise IntakeError unless this is a readable PDF within the limits. Returns its page count."""
    if Path(file_name).suffix.lower() != ".pdf":
        raise IntakeError(f"{file_name}: only PDF files are supported")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise IntakeError(f"{file_name}: file exceeds {settings.MAX_UPLOAD_MB} MB")
    try:
        pages = len(pdfium.PdfDocument(data))
    except pdfium.PdfiumError as e:
        raise IntakeError(f"{file_name}: not a readable PDF ({e})") from e
    if pages > settings.MAX_PAGES:
        raise IntakeError(f"{file_name}: {pages} pages (max {settings.MAX_PAGES})")
    return pages


def find_duplicate(data: bytes, dataset_id: str) -> dict | None:
    """The same file already in this dataset (any status), or None."""
    return documents().find_one({"dataset_id": dataset_id, "file.sha256": file_sha256(data)})


def register_upload(data: bytes, file_name: str, dataset_id: str) -> dict | None:
    """Store the PDF and create its queued document record. None if already in the dataset."""
    pages = check_upload(data, file_name)
    existing = find_duplicate(data, dataset_id)
    if existing and existing["processing"]["status"] != "failed":
        log.info("Duplicate skipped: %s", file_name)
        return None
    if existing:  # a failed earlier attempt: start again from scratch
        from backend.library import delete_document

        delete_document(existing)

    gridfs_id = get_fs().put(data, filename=file_name, content_type="application/pdf")
    doc = {
        "_id": make_id("doc_"),
        "dataset_id": dataset_id,
        "file": {"name": file_name, "sha256": file_sha256(data), "bytes": len(data), "gridfs_id": str(gridfs_id)},
        "metadata": {"title": "", "page_count": pages},
        "processing": {"status": "queued", "pages_done": 0, "pages_total": pages, "error": None},
        "stats": {},
        "outline": [],
        "pages": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    documents().insert_one(doc)
    log.info("Registered %s as %s", file_name, doc["_id"])
    return doc
