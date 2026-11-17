"""Create regular and Atlas Search indexes."""

import logging

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.operations import SearchIndexModel

from backend.db.client import get_db

log = logging.getLogger(__name__)


def ensure_regular_indexes() -> None:
    """Create regular indexes on all collections."""
    db = get_db()

    db.chunks.create_indexes(
        [
            IndexModel([("document_id", ASCENDING), ("seq", ASCENDING)], unique=True),
        ]
    )
    db.documents.create_indexes(
        [
            IndexModel([("dataset_id", ASCENDING), ("file.sha256", ASCENDING)], unique=True),
            IndexModel([("processing.status", ASCENDING)]),
        ]
    )
    db.queries.create_indexes(
        [
            IndexModel([("dataset_id", ASCENDING), ("ts", DESCENDING)]),
            IndexModel([("session_id", ASCENDING), ("turn", ASCENDING)]),
        ]
    )
    db.sessions.create_indexes(
        [
            IndexModel([("dataset_id", ASCENDING), ("updated_at", DESCENDING)]),
        ]
    )
    log.info("Regular indexes ensured")


VECTOR_INDEX_DEF = {
    "fields": [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": 768,
            "similarity": "cosine",
            "quantization": "scalar",
        },
        {"type": "filter", "path": "dataset_id"},
        {"type": "filter", "path": "document_id"},
    ]
}

TEXT_INDEX_DEF = {
    "mappings": {
        "dynamic": False,
        "fields": {
            "embed_text": {"type": "string", "analyzer": "lucene.english"},
            "dataset_id": {"type": "token"},
            "document_id": {"type": "token"},
        },
    }
}


def ensure_search_indexes() -> None:
    """Create Atlas Vector Search and Atlas Search indexes if they don't exist."""
    db = get_db()
    existing = {idx["name"] for idx in db.chunks.list_search_indexes()}

    if "chunks_vec" not in existing:
        db.chunks.create_search_index(
            SearchIndexModel(definition=VECTOR_INDEX_DEF, name="chunks_vec", type="vectorSearch")
        )
        log.info("Created chunks_vec vector index")

    if "chunks_text" not in existing:
        db.chunks.create_search_index(
            SearchIndexModel(definition=TEXT_INDEX_DEF, name="chunks_text", type="search")
        )
        log.info("Created chunks_text search index")


def ensure_all_indexes() -> None:
    """Create all indexes."""
    ensure_regular_indexes()
    ensure_search_indexes()
