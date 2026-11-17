"""Query log, one query's full trace, and feedback."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.api.deps import get_or_404
from backend.db.client import queries

router = APIRouter(tags=["queries"])
LOG_FIELDS = {
    "question": 1,
    "decision": 1,
    "trust": 1,
    "ts": 1,
    "latency_ms.total": 1,
    "session_id": 1,
    "feedback.value": 1,
    "answer": 1,
}


class Feedback(BaseModel):
    value: bool  # True = thumbs up (answer was correct)
    reason: str | None = None


@router.get("/queries")
def log(
    dataset_id: str | None = None,
    decision: str | None = None,
    complete: bool = False,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Newest first. Returns {items, total} for paging."""
    match = {k: v for k, v in (("dataset_id", dataset_id), ("decision", decision)) if v}
    if complete:
        match["score_card"] = {"$exists": True}
    items = list(queries().find(match, LOG_FIELDS).sort("ts", -1).skip(skip).limit(limit))
    return {"items": items, "total": queries().count_documents(match)}


@router.get("/queries/{query_id}")
def get(query_id: str):
    """Full trace of one question."""
    return get_or_404(queries(), query_id, "Query")


@router.post("/queries/{query_id}/feedback")
def feedback(query_id: str, body: Feedback):
    """Store thumbs up/down on a query."""
    get_or_404(queries(), query_id, "Query")
    queries().update_one({"_id": query_id}, {"$set": {"feedback": body.model_dump()}})
    return {"ok": True}
