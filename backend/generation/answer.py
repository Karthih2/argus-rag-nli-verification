"""Draft an answer as cited claims: one LLM call, validated, retried once, sentence fallback."""

import logging

import pysbd
from pydantic import ValidationError

from backend.generation.llm import call_llm
from backend.generation.prompts import ANSWER_SYSTEM, ANSWER_USER
from backend.generation.schemas import AnswerOutput, Claim

log = logging.getLogger(__name__)

_segmenter = pysbd.Segmenter(language="en", clean=False)


def generate_answer(question: str, context: str) -> AnswerOutput:
    """First draft for a question over the numbered context."""
    user = ANSWER_USER.format(context=context, question=question)
    return draft(ANSWER_SYSTEM, user)


def draft(system: str, user: str, use_cache: bool = True) -> AnswerOutput:
    """Call the LLM and validate. Retry once uncached; then fall back to sentence claims."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    raw: dict = {}
    for attempt_cache in (use_cache, False):
        raw = call_llm(messages, json_mode=True, reasoning_effort="medium", use_cache=attempt_cache)
        try:
            return AnswerOutput.model_validate({**raw, "model": raw.get("_model", "")})
        except ValidationError as e:
            log.warning("Answer JSON invalid, retrying: %s", e)
    return _sentence_fallback(raw)


def _sentence_fallback(raw: dict) -> AnswerOutput:
    """If claims are unusable, every answer sentence becomes an uncited claim."""
    text = str(raw.get("answer", ""))
    claims = [Claim(text=s.strip()) for s in _segmenter.segment(text) if s.strip()]
    return AnswerOutput(answer=text, claims=claims, model=raw.get("_model", ""))
