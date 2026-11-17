"""POST /api/ask: run one question and stream its stages over Server-Sent Events."""

import asyncio
import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_or_404
from backend.db.client import sessions
from backend.pipeline import run_question

router = APIRouter(tags=["ask"])
log = logging.getLogger(__name__)
_DONE = object()


class AskRequest(BaseModel):
    session_id: str
    question: str


@router.post("/ask")
def ask(body: AskRequest):
    """Stage events while working, then one 'result' event (spec 12.1) or an 'error' event."""
    session = get_or_404(sessions(), body.session_id, "Session")
    return EventSourceResponse(_events(body.question, session))


async def _events(question: str, session: dict):
    loop = asyncio.get_running_loop()
    events: asyncio.Queue = asyncio.Queue()

    def emit(kind: str, data) -> None:
        loop.call_soon_threadsafe(events.put_nowait, (kind, data))

    def work() -> None:
        # Runs in a worker thread so one slow question never blocks the server.
        try:
            result = run_question(
                question,
                session["dataset_id"],
                session.get("document_ids") or None,
                session,
                on_stage=lambda e: emit("stage", e),
            )
            emit("result", result)
        except Exception as e:  # noqa: BLE001 - report any pipeline failure to the client
            log.exception("Pipeline error")
            emit("error", {"error": str(e)})
        finally:
            emit(_DONE, None)

    task = loop.run_in_executor(None, work)
    while (item := await events.get())[0] is not _DONE:
        yield {"event": item[0], "data": json.dumps(item[1], default=str)}
    await task
