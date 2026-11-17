"""Number parsing and comparison for verification and synthetic number swaps.

Handles:
- Digit numbers: 7, 1.5, 1,500,000
- Word numbers: "seven" → 7, "twenty-three" → 23  (word2number library)
- Scale words: "1.5 million" → 1,500,000, "$2.3 billion" → 2,300,000,000
- Currency: $1,500, $1.5 million
- Percentages: 22%, 22 percent
- Durations: 7 years, seven years
- Negative numbers: -5, negative five
"""

import logging
import re
from dataclasses import dataclass

from word2number import w2n

log = logging.getLogger(__name__)

SCALES = {
    "hundred": 1e2, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12,
    "hundreds": 1e2, "thousands": 1e3, "millions": 1e6, "billions": 1e9, "trillions": 1e12,
}


@dataclass
class ParsedNumber:
    raw: str
    value: float
    unit: str
    span: tuple[int, int]


# --- Digit-based patterns (most specific first) ---
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(%|percent|pct)\b", re.IGNORECASE)
_DURATION = re.compile(
    r"(\d+(?:\.\d+)?)\s*(years?|months?|days?|hours?|minutes?|seconds?|weeks?)\b",
    re.IGNORECASE,
)
_CURRENCY_SCALE = re.compile(
    r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(hundred|thousand|million|billion|trillion)s?\b",
    re.IGNORECASE,
)
_CURRENCY = re.compile(r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)")
_DIGIT_SCALE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*(hundred|thousand|million|billion|trillion)s?\b",
    re.IGNORECASE,
)
_COMMA_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?)(?![\w,])")
_PLAIN_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\w)")

# Word number pattern: sequences of number words (one, twenty-three, etc.)
_WORD_NUM = re.compile(
    r"(?:(?:negative|minus)\s+)?"
    r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion)"
    r"(?:[\s-]+|$))+"
    r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion))?",
    re.IGNORECASE,
)

_WORD_DURATION = re.compile(
    r"(?:(?:negative|minus)\s+)?"
    r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion)"
    r"(?:[\s-]+|$))+"
    r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion))?"
    r"\s*(years?|months?|days?|hours?|minutes?|seconds?|weeks?)\b",
    re.IGNORECASE,
)


def _overlaps(span: tuple[int, int], taken: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in taken)


def _parse_word_number(text: str) -> float | None:
    """Parse a word-number string like 'seven' or 'twenty-three' or 'one million'."""
    clean = text.strip().lower()
    negative = False
    if clean.startswith(("negative ", "minus ")):
        negative = True
        clean = clean.split(None, 1)[1]
    try:
        val = float(w2n.word_to_num(clean))
        return -val if negative else val
    except (ValueError, IndexError):
        return None


def parse_numbers(text: str) -> list[ParsedNumber]:
    """Every number in text with its normalised value, unit and position."""
    found: list[ParsedNumber] = []
    taken: list[tuple[int, int]] = []

    # Digit-based patterns (most specific first)
    digit_patterns = [
        (_PERCENT, lambda m: "%", lambda m: float(m.group(1).replace(",", ""))),
        (_DURATION, lambda m: m.group(2).lower().rstrip("s"), lambda m: float(m.group(1).replace(",", ""))),
        (_CURRENCY_SCALE, lambda m: "USD", lambda m: float(m.group(1).replace(",", "")) * SCALES.get(m.group(2).lower().rstrip("s"), 1)),
        (_CURRENCY, lambda m: "USD", lambda m: float(m.group(1).replace(",", ""))),
        (_DIGIT_SCALE, lambda m: "", lambda m: float(m.group(1).replace(",", "")) * SCALES.get(m.group(2).lower().rstrip("s"), 1)),
        (_COMMA_NUM, lambda m: "", lambda m: float(m.group(1).replace(",", ""))),
        (_PLAIN_NUM, lambda m: "", lambda m: float(m.group(1).replace(",", ""))),
    ]
    for pattern, unit_of, value_of in digit_patterns:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if _overlaps(span, taken):
                continue
            found.append(ParsedNumber(m.group(0), value_of(m), unit_of(m), span))
            taken.append(span)

    # Word-based duration ("seven years")
    for m in _WORD_DURATION.finditer(text):
        span = (m.start(), m.end())
        if _overlaps(span, taken):
            continue
        num_part = m.group(0)
        unit_match = re.search(r"(years?|months?|days?|hours?|minutes?|seconds?|weeks?)\s*$", num_part, re.IGNORECASE)
        if unit_match:
            num_text = num_part[:unit_match.start()].strip()
            unit = unit_match.group(1).lower().rstrip("s")
        else:
            continue
        val = _parse_word_number(num_text)
        if val is not None:
            found.append(ParsedNumber(m.group(0).strip(), val, unit, span))
            taken.append(span)

    # Word-based numbers ("seven", "twenty-three", "one million")
    for m in _WORD_NUM.finditer(text):
        span = (m.start(), m.end())
        if _overlaps(span, taken):
            continue
        val = _parse_word_number(m.group(0))
        if val is not None:
            found.append(ParsedNumber(m.group(0).strip(), val, "", span))
            taken.append(span)

    return sorted(found, key=lambda n: n.span[0])


def missing_numbers(claim: str, evidence: str) -> list[ParsedNumber]:
    """Numbers in claim not present (same value and unit) in evidence."""
    have = {(n.value, n.unit) for n in parse_numbers(evidence)}
    return [n for n in parse_numbers(claim) if not _found(n, have)]


def _found(n: ParsedNumber, have: set[tuple[float, str]]) -> bool:
    # Unit missing on either side still matches ("7" vs "7 years").
    return any(v == n.value and (u == n.unit or not u or not n.unit) for v, u in have)
