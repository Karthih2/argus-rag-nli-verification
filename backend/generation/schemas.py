"""Pydantic models for LLM answer output."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator


def _coerce_cites(v: object) -> list[str]:
    """LLM sometimes returns a bare string like 'C1' instead of ['C1']."""
    if isinstance(v, str):
        return [v]
    return v  # type: ignore[return-value]


class Claim(BaseModel):
    text: str
    cites: Annotated[list[str], BeforeValidator(_coerce_cites)] = []
    quote: str = ""


class AnswerOutput(BaseModel):
    answer: str
    claims: list[Claim] = []
    not_found: bool = False
    model: str = ""
