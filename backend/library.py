"""Datasets and documents: create, and delete with everything derived from them."""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from gridfs.errors import NoFile

from backend.common.ids import make_id
from backend.db.client import chunks, datasets, documents, get_fs, queries, sessions

log = logging.getLogger(__name__)


def create_dataset(name: str, description: str = "", dataset_id: str | None = None, **settings) -> dict:
    """New dataset."""
    ds = {
        "_id": dataset_id or make_id("ds_"),
        "name": name,
        "description": description,
        "settings": dict(settings),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    datasets().insert_one(ds)
    return ds


def delete_gridfs_file(file_id: str | None) -> None:
    """Remove a stored original PDF; quietly skip one that is already gone."""
    if not file_id:
        return
    try:
        get_fs().delete(ObjectId(file_id))
    except (NoFile, InvalidId):
        log.warning("GridFS file %s already gone", file_id)


def delete_document(doc: dict) -> None:
    """Remove a document, its chunks and its original PDF."""
    delete_gridfs_file(doc.get("file", {}).get("gridfs_id"))
    chunks().delete_many({"document_id": doc["_id"]})
    documents().delete_one({"_id": doc["_id"]})
    log.info("Deleted document %s", doc["_id"])


def delete_dataset(dataset_id: str) -> None:
    """Remove a dataset and everything in it."""
    for doc in documents().find({"dataset_id": dataset_id}):
        delete_document(doc)
    for coll in (sessions, queries):
        coll().delete_many({"dataset_id": dataset_id})
    datasets().delete_one({"_id": dataset_id})
