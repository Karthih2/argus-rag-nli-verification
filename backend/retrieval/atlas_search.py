"""Atlas Vector Search and Atlas Search queries on chunks, filtered to a dataset and documents."""

import logging
import time

from backend.config import settings
from backend.db.client import chunks
from backend.retrieval.embedder import embed_query

log = logging.getLogger(__name__)

HIDE_VECTOR = {"$project": {"embedding": 0}}
POLL_S = 2


def vector_search(
    question: str, dataset_id: str, document_ids: list[str] | None = None, limit: int | None = None
) -> list[dict]:
    """Semantic search with $vectorSearch."""
    return _vector_search(embed_query(question), dataset_id, document_ids, limit or settings.RETRIEVE_LIMIT)


def text_search(
    question: str, dataset_id: str, document_ids: list[str] | None = None, limit: int | None = None
) -> list[dict]:
    """Keyword search with $search on embed_text."""
    filters = [{"equals": {"path": "dataset_id", "value": dataset_id}}]
    if document_ids:
        filters.append({"in": {"path": "document_id", "value": document_ids}})
    pipeline = [
        {
            "$search": {
                "index": "chunks_text",
                "compound": {
                    "must": [{"text": {"query": question, "path": "embed_text"}}],
                    "filter": filters,
                },
            }
        },
        {"$limit": limit or settings.RETRIEVE_LIMIT},
        {"$addFields": {"_ts_score": {"$meta": "searchScore"}}},
        HIDE_VECTOR,
    ]
    return list(chunks().aggregate(pipeline))


def is_searchable(dataset_id: str, document_id: str) -> bool:
    """True once $vectorSearch filtered to this document returns a hit (indexes update async)."""
    probe = chunks().find_one({"document_id": document_id}, {"embedding": 1})
    if not probe:
        return False
    return bool(_vector_search(list(probe["embedding"].as_vector().data), dataset_id, [document_id], 1))


def wait_until_searchable(dataset_id: str, document_id: str) -> bool:
    """Poll is_searchable until it succeeds or INDEX_READY_TIMEOUT_S passes."""
    deadline = time.monotonic() + settings.INDEX_READY_TIMEOUT_S
    while time.monotonic() < deadline:
        if is_searchable(dataset_id, document_id):
            return True
        time.sleep(POLL_S)
    return False


def _vector_search(
    vector: list[float], dataset_id: str, document_ids: list[str] | None, limit: int
) -> list[dict]:
    filters: dict = {"dataset_id": dataset_id}
    if document_ids:
        filters["document_id"] = {"$in": document_ids}
    pipeline = [
        {
            "$vectorSearch": {
                "index": "chunks_vec",
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(settings.NUM_CANDIDATES, limit),
                "limit": limit,
                "filter": filters,
            }
        },
        {"$addFields": {"_vs_score": {"$meta": "vectorSearchScore"}}},
        HIDE_VECTOR,
    ]
    return list(chunks().aggregate(pipeline))
