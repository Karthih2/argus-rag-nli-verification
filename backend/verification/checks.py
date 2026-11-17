"""Extra checks beside NLI: evidence quote, quotations in the claim, numbers."""

from rapidfuzz import fuzz

from backend.common.numbers import missing_numbers
from backend.common.text import quoted_strings
from backend.config import settings

QUOTE_MIN = 0.90
QUOTATION_MIN = 0.95
MIN_QUOTATION_CHARS = 5


def find_quote(quote: str, text: str) -> tuple[bool, float, list[int] | None]:
    """Is the claim's evidence quote in the text? Returns (found, score 0-1, [start, end]).

    A quote shorter than QUOTE_MIN_CHARS is treated as not found — prevents
    trivial matches like a single digit.
    """
    if not quote or not text or len(quote.strip()) < settings.QUOTE_MIN_CHARS:
        return False, 0.0, None
    match = fuzz.partial_ratio_alignment(quote, text)
    score = match.score / 100.0
    span = [match.dest_start, match.dest_end] if score >= QUOTE_MIN else None
    return score >= QUOTE_MIN, score, span


def quotations_ok(claim: str, text: str) -> bool:
    """A quotation the claim presents ("...") must match the source almost exactly."""
    return all(
        fuzz.partial_ratio(q, text) / 100.0 >= QUOTATION_MIN
        for q in quoted_strings(claim)
        if len(q) >= MIN_QUOTATION_CHARS
    )


def number_problems(claim: str, evidence: str) -> str:
    """'' if every number in the claim is in the evidence, else a short explanation."""
    return "; ".join(f"claim says {n.raw}, not in the source" for n in missing_numbers(claim, evidence))
