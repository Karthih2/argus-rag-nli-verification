"""Draft an answer as cited claims: one LLM call, validated, retried once, sentence fallback."""

import logging

from pydantic import ValidationError

from backend.common.text import sentences
from backend.generation.llm import call_llm
from backend.generation.prompts import ANSWER_SYSTEM, ANSWER_USER, RETRY_NOTE
from backend.generation.schemas import AnswerOutput, Claim

log = logging.getLogger(__name__)


def generate_answer(question: str, context: str, retry_not_found: bool = False) -> AnswerOutput:
    """Draft for a question over the numbered context. The retry adds a note and skips the cache."""
    user = ANSWER_USER.format(context=context, question=question)
    if retry_not_found:
        return draft(ANSWER_SYSTEM, user + RETRY_NOTE, use_cache=False)
    return draft(ANSWER_SYSTEM, user)


def draft(system: str, user: str, use_cache: bool | None = None) -> AnswerOutput:
    """Call the LLM and validate. Retry once uncached; then fall back to sentence claims."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    raw: dict = {}
    for attempt_cache in (use_cache, False):
        raw = call_llm(messages, json_mode=True, reasoning_effort="medium", use_cache=attempt_cache)
        try:
            out = AnswerOutput.model_validate({**raw, "model": raw.get("_model", "")})
        except ValidationError as e:
            log.warning("Answer JSON invalid, retrying: %s", e)
            continue
        return out if out.not_found or out.claims else _sentence_fallback(raw)
    return _sentence_fallback(raw)


def _sentence_fallback(raw: dict) -> AnswerOutput:
    """When claims are missing or unusable, each answer sentence becomes an uncited claim."""
    text = str(raw.get("answer", "")).strip()
    claims = [Claim(text=s) for s in sentences(text)]
    return AnswerOutput(answer=text, claims=claims, not_found=not claims, model=raw.get("_model", ""))
