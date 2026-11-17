"""Conversations: create and running score totals. Each question is answered on its own."""

from datetime import datetime, timezone

from pymongo import ReturnDocument

from backend.common.ids import make_id
from backend.db.client import sessions
from backend.verification.aggregate import DECISIONS

ANSWER_PREVIEW_CHARS = 200


def create_session(dataset_id: str, document_ids: list[str], title: str = "") -> dict:
    """Start a conversation over the selected documents."""
    session = {
        "_id": make_id("s_"),
        "dataset_id": dataset_id,
        "title": title,
        "document_ids": document_ids,
        "mode": "cross" if len(document_ids) > 1 else "single",
        "turns": 0,
        "trust_sum": 0,
        "summary": {**dict.fromkeys(DECISIONS, 0), "avg_trust": 0},
        "updated_at": _now(),
    }
    sessions().insert_one(session)
    return session


def get_session(session_id: str) -> dict | None:
    return sessions().find_one({"_id": session_id})


def record_turn(session_id: str, question: str, answer: str, decision: str, trust: int) -> dict:
    """Increment turn count and update totals. Returns the new summary."""
    session = sessions().find_one_and_update(
        {"_id": session_id},
        {
            "$inc": {"turns": 1, "trust_sum": trust, f"summary.{decision}": 1},
            "$set": {"updated_at": _now()},
        },
        return_document=ReturnDocument.AFTER,
    )
    avg = round(session["trust_sum"] / session["turns"])
    sessions().update_one({"_id": session_id}, {"$set": {"summary.avg_trust": avg}})
    if not session.get("title"):
        sessions().update_one({"_id": session_id}, {"$set": {"title": question[:60]}})
    return {"turns": session["turns"], **session["summary"], "avg_trust": avg}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
