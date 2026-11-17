"""Pydantic models for LLM answer output."""

from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    cites: list[str] = []
    quote: str = ""


class AnswerOutput(BaseModel):
    answer: str
    claims: list[Claim] = []
    not_found: bool = False
    model: str = ""
