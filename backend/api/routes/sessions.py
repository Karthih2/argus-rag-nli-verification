"""Conversation routes: start, list, open with all turns."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.api.deps import get_or_404
from backend.db.client import datasets, queries
from backend.db.client import sessions as sessions_coll
from backend.sessions import create_session

router = APIRouter(tags=["sessions"])
LIST_LIMIT = 50


class SessionCreate(BaseModel):
    dataset_id: str
    document_ids: list[str] = []
    title: str = ""


@router.post("/sessions")
def start(body: SessionCreate):
    get_or_404(datasets(), body.dataset_id, "Dataset")
    return create_session(body.dataset_id, body.document_ids, body.title)


@router.get("/sessions")
def list_all(dataset_id: str | None = None):
    query = {"dataset_id": dataset_id} if dataset_id else {}
    return list(sessions_coll().find(query).sort("updated_at", -1).limit(LIST_LIMIT))


@router.get("/sessions/{session_id}")
def open_session(session_id: str):
    session = get_or_404(sessions_coll(), session_id, "Session")
    return {"session": session, "turns": list(queries().find({"session_id": session_id}).sort("turn", 1))}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    get_or_404(sessions_coll(), session_id, "Session")
    sessions_coll().delete_one({"_id": session_id})
    queries().delete_many({"session_id": session_id})
    return {"ok": True, "deleted": session_id}

