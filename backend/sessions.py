"""Conversations: create and running score totals. Each question is answered on its own."""

from datetime import datetime, timezone

from pymongo import ReturnDocument

from backend.common.ids import make_id
from backend.db.client import sessions
from backend.verification.aggregate import DECISIONS

TITLE_CHARS = 60


def create_session(dataset_id: str, document_ids: list[str], title: str = "") -> dict:
    """Start a conversation over the selected documents."""
    session = {
        "_id": make_id("s_"),
        "dataset_id": dataset_id,
        "title": title,
        "document_ids": document_ids,
        "mode": "cross" if len(document_ids) > 1 else "single",
        "turns": 0,
        "scored_turns": 0,
        "trust_sum": 0,
        "summary": {**dict.fromkeys(DECISIONS, 0), "avg_trust": None},
        "updated_at": _now(),
    }
    sessions().insert_one(session)
    return session


def get_session(session_id: str) -> dict | None:
    return sessions().find_one({"_id": session_id})


def record_turn(session_id: str, question: str, decision: str, trust: int | None) -> dict:
    """Count the turn and its decision; average trust over the answers that have one."""
    inc = {"turns": 1, f"summary.{decision}": 1}
    if trust is not None:
        inc.update({"scored_turns": 1, "trust_sum": trust})
    session = sessions().find_one_and_update(
        {"_id": session_id},
        {"$inc": inc, "$set": {"updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    scored = session.get("scored_turns", 0)
    avg = round(session["trust_sum"] / scored) if scored else None
    update = {"summary.avg_trust": avg}
    if not session.get("title"):
        update["title"] = question[:TITLE_CHARS]
    sessions().update_one({"_id": session_id}, {"$set": update})
    return {"turns": session["turns"], **session["summary"], "avg_trust": avg}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
