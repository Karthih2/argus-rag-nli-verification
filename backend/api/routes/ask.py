"""POST /api/ask: run one question and stream its stages over Server-Sent Events."""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_or_404
from backend.config import settings
from backend.db.client import sessions
from backend.pipeline import run_question

router = APIRouter(tags=["ask"])
log = logging.getLogger(__name__)
_DONE = object()
_WINDOW_S = 60
_recent: dict[str, deque] = defaultdict(deque)


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=2000)


@router.post("/ask")
def ask(body: AskRequest, request: Request):
    """Stage events while working, then one 'result' event or an 'error' event."""
    _rate_limit(request.client.host if request.client else "unknown")
    session = get_or_404(sessions(), body.session_id, "Session")
    return EventSourceResponse(_events(body.question.strip(), session))


def _rate_limit(ip: str) -> None:
    """At most RATE_LIMIT_PER_MINUTE questions per client IP (protects the Groq key on a public demo)."""
    now, hits = time.monotonic(), _recent[ip]
    while hits and now - hits[0] > _WINDOW_S:
        hits.popleft()
    if len(hits) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(429, "Too many questions; please wait a minute.")
    hits.append(now)


async def _events(question: str, session: dict):
    loop = asyncio.get_running_loop()
    events: asyncio.Queue = asyncio.Queue()

    def emit(kind, data) -> None:
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
