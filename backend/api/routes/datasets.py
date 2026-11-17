"""Dataset routes: create, list, delete."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.api.deps import get_or_404, writable_dataset
from backend.db.client import datasets, documents, sessions
from backend.library import create_dataset, delete_dataset

router = APIRouter(tags=["datasets"])


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


@router.post("/datasets")
def create(body: DatasetCreate):
    return _summary(create_dataset(**body.model_dump()))


@router.get("/datasets")
def list_all():
    """All datasets with document, page and chat counts."""
    return [_summary(ds) for ds in datasets().find().sort("created_at", -1)]


@router.get("/datasets/{dataset_id}")
def get(dataset_id: str):
    return _summary(get_or_404(datasets(), dataset_id, "Dataset"))


@router.delete("/datasets/{dataset_id}")
def delete(dataset_id: str):
    writable_dataset(dataset_id)
    delete_dataset(dataset_id)
    return {"deleted": dataset_id}


def _summary(ds: dict) -> dict:
    docs = list(documents().find({"dataset_id": ds["_id"]}, {"metadata.page_count": 1, "stats": 1}))
    return {
        **ds,
        "document_count": len(docs),
        "page_count": sum(d.get("metadata", {}).get("page_count", 0) for d in docs),
        "table_count": sum(d.get("stats", {}).get("tables", 0) for d in docs),
        "image_count": sum(
            d.get("stats", {}).get("charts", 0) + d.get("stats", {}).get("photos", 0) for d in docs
        ),
        "chat_count": sessions().count_documents({"dataset_id": ds["_id"]}),
        "read_only": bool(ds.get("settings", {}).get("read_only")),
    }
