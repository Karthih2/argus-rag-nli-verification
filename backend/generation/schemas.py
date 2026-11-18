"""Pydantic models for LLM answer output."""

import re
from typing import Annotated

from pydantic import BaseModel, BeforeValidator

REF_RE = re.compile(r"\b[CN]\d+\b")


def _coerce_cites(v: object) -> list[str]:
    """Context refs from whatever shape the LLM returns: 'C1', '[C1]', 'C1, C2', ['[C2]'], None."""
    if v is None:
        return []
    items = [v] if isinstance(v, str) else v if isinstance(v, list) else [str(v)]
    refs = [r for item in items for r in REF_RE.findall(str(item).upper())]
    return list(dict.fromkeys(refs))


class Claim(BaseModel):
    text: str
    cites: Annotated[list[str], BeforeValidator(_coerce_cites)] = []
    quote: str = ""


class AnswerOutput(BaseModel):
    answer: str
    claims: list[Claim] = []
    not_found: bool = False
    model: str = ""
