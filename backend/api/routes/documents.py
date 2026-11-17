"""Document routes: upload (queued for background ingestion), list, status, delete.

Upload accepts PDF and Word files (.pdf, .doc, .docx), max MAX_FILES_PER_UPLOAD at a time.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.api.deps import get_or_404, writable_dataset
from backend.config import settings
from backend.db.client import documents
from backend.ingestion.intake import ALLOWED_EXTENSIONS, IntakeError, check_limits, validate_file_type
from backend.library import delete_document
from backend.worker import ingest_job

router = APIRouter(tags=["documents"])


@router.post("/datasets/{dataset_id}/documents")
async def upload(dataset_id: str, background: BackgroundTasks, files: list[UploadFile] = File(...)):
    """Accept up to MAX_FILES_PER_UPLOAD documents (PDF/DOCX); each is ingested in the background."""
    writable_dataset(dataset_id)
    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            400,
            f"Too many files: {len(files)} (max {settings.MAX_FILES_PER_UPLOAD} per upload)",
        )
    queued = []
    for f in files:
        name = Path(f.filename or "upload.pdf").name
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                400,
                f"{name}: unsupported file type. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        data = await f.read()
        try:
            validate_file_type(name)
            check_limits(data, name)
        except IntakeError as e:
            raise HTTPException(400, f"{name}: {e}") from e
        path = Path(tempfile.mkdtemp()) / name
        path.write_bytes(data)
        background.add_task(ingest_job, path, dataset_id, name)
        queued.append({"file_name": name, "bytes": len(data)})
    return {"status": "queued", "files": queued}


@router.get("/datasets/{dataset_id}/documents")
def list_for_dataset(dataset_id: str):
    return list(documents().find({"dataset_id": dataset_id}).sort("created_at", -1))


@router.get("/documents/{document_id}")
def get(document_id: str):
    """Status, extraction report and outline."""
    return get_or_404(documents(), document_id, "Document")


@router.delete("/documents/{document_id}")
def delete(document_id: str):
    """Delete the document and everything derived from it."""
    doc = get_or_404(documents(), document_id, "Document")
    writable_dataset(doc["dataset_id"])
    if doc["processing"]["status"] not in ("ready", "failed"):
        raise HTTPException(409, "Document is still being processed; delete it when it is ready or failed")
    delete_document(doc)
    return {"deleted": document_id}
