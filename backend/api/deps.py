"""Small helpers shared by the API routes."""

from fastapi import HTTPException
from pymongo.collection import Collection

from backend.db.client import datasets


def get_or_404(collection: Collection, record_id: str, what: str) -> dict:
    """Fetch a record by _id or raise 404 '<what> not found'."""
    record = collection.find_one({"_id": record_id})
    if record is None:
        raise HTTPException(404, f"{what} not found")
    return record


def writable_dataset(dataset_id: str) -> dict:
    """The dataset, or 403 if it is the read-only demo (public visitors can't change it)."""
    ds = get_or_404(datasets(), dataset_id, "Dataset")
    if ds.get("settings", {}).get("read_only"):
        raise HTTPException(403, "The demo dataset is read-only. Upload your PDFs to a new dataset.")
    return ds
