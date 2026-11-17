"""Upload intake: size/page/count limits, hash, deduplicate, store the original in GridFS.

Accepted file types: PDF (.pdf), Word (.doc, .docx).
Limits are in config.py: MAX_UPLOAD_MB, MAX_PAGES, MAX_FILES_PER_UPLOAD.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.common.ids import file_sha256, make_id
from backend.config import settings
from backend.db.client import documents, get_fs

log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class IntakeError(ValueError):
    """The upload breaks a limit (size, pages, type) or isn't readable."""


def validate_file_type(file_name: str) -> str:
    """Check extension is allowed. Returns the normalised extension."""
    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise IntakeError(
            f"{file_name}: unsupported file type '{ext}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def check_limits(data: bytes, file_name: str) -> int:
    """Raise IntakeError if the file is too big or unreadable. Returns page count (0 for non-PDF)."""
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise IntakeError(f"File exceeds {settings.MAX_UPLOAD_MB} MB")

    ext = Path(file_name).suffix.lower()
    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium
            pages = len(pdfium.PdfDocument(data))
        except Exception as e:
            raise IntakeError(f"Not a readable PDF: {e}") from e
        if pages > settings.MAX_PAGES:
            raise IntakeError(f"PDF has {pages} pages (max {settings.MAX_PAGES})")
        return pages
    # For DOCX files, page count is not easily determined without rendering
    return 0


def register_upload(data: bytes, file_name: str, dataset_id: str) -> dict | None:
    """Store the file and create its queued document record. None if already in the dataset."""
    ext = validate_file_type(file_name)
    pages = check_limits(data, file_name)
    sha = file_sha256(data)
    existing = documents().find_one({"dataset_id": dataset_id, "file.sha256": sha})
    if existing and existing["processing"]["status"] != "failed":
        log.info("Duplicate skipped: %s (sha=%s)", file_name, sha[:12])
        return None
    if existing:  # a failed earlier attempt: start again from scratch
        from backend.library import delete_document
        delete_document(existing)

    content_type = MIME_TYPES.get(ext, "application/octet-stream")
    gridfs_id = get_fs().put(data, filename=file_name, content_type=content_type)
    doc = {
        "_id": make_id("doc_"),
        "dataset_id": dataset_id,
        "file": {
            "name": file_name,
            "sha256": sha,
            "bytes": len(data),
            "gridfs_id": str(gridfs_id),
            "type": ext.lstrip("."),
        },
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
