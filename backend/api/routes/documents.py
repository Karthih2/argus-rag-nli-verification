"""Document routes: upload (ingested in the background), list, status, delete. PDF only."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.api.deps import get_or_404, writable_dataset
from backend.config import settings
from backend.db.client import documents
from backend.ingestion.intake import IntakeError, check_upload, find_duplicate
from backend.ingestion.pipeline import refresh_indexing
from backend.library import delete_document
from backend.worker import ingest_job

router = APIRouter(tags=["documents"])
DELETABLE = ("ready", "failed", "indexing")


@router.post("/datasets/{dataset_id}/documents")
async def upload(dataset_id: str, background: BackgroundTasks, files: list[UploadFile] = File(...)):
    """Check every file first, then queue the new ones; files already in the dataset are skipped."""
    writable_dataset(dataset_id)
    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(400, f"Too many files: {len(files)} (max {settings.MAX_FILES_PER_UPLOAD} per upload)")
    accepted = []
    for f in files:
        name = Path(f.filename or "upload.pdf").name
        data = await f.read()
        try:
            check_upload(data, name)
        except IntakeError as e:
            raise HTTPException(400, str(e)) from e
        accepted.append((name, data))

    queued, skipped = [], []
    for name, data in accepted:
        existing = find_duplicate(data, dataset_id)
        if existing and existing["processing"]["status"] != "failed":
            skipped.append({"file_name": name, "reason": "already in this dataset", "document_id": existing["_id"]})
            continue
        path = Path(tempfile.mkdtemp()) / name
        path.write_bytes(data)
        background.add_task(ingest_job, path, dataset_id, name)
        queued.append({"file_name": name, "bytes": len(data)})
    return {"status": "queued" if queued else "skipped", "files": queued, "skipped": skipped}


@router.get("/datasets/{dataset_id}/documents")
def list_for_dataset(dataset_id: str):
    return [refresh_indexing(d) for d in documents().find({"dataset_id": dataset_id}).sort("created_at", -1)]


@router.get("/documents/{document_id}")
def get(document_id: str):
    """Status, extraction report and outline."""
    return refresh_indexing(get_or_404(documents(), document_id, "Document"))


@router.delete("/documents/{document_id}")
def delete(document_id: str):
    """Delete the document and everything derived from it."""
    doc = get_or_404(documents(), document_id, "Document")
    writable_dataset(doc["dataset_id"])
    if doc["processing"]["status"] not in DELETABLE:
        raise HTTPException(409, "Document is still being processed; delete it once it is ready or failed")
    delete_document(doc)
    return {"deleted": document_id}
