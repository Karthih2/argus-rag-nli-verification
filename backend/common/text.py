"""Text normalisation and helpers shared by chunking, checks and search text."""

import re
import unicodedata

QUOTE_RE = re.compile(r'["“„](.*?)["”‟]')


def normalise(text: str) -> str:
    """Normalise unicode and whitespace for comparison."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_spans(text: str) -> list[list[int]]:
    """[start, end] of every quoted span in text."""
    return [[m.start(), m.end()] for m in QUOTE_RE.finditer(text)]


def quoted_strings(text: str) -> list[str]:
    """The text inside every quoted span."""
    return QUOTE_RE.findall(text)


def evidence_text(chunk: dict) -> str:
    """What a chunk offers as evidence: its text."""
    return chunk.get("text", "")


def approx_tokens(text: str) -> int:
    """Cheap token estimate (about 4 characters per token) for budgets."""
    return len(text) // 4


_nli_tokenizer = None


def nli_token_count(text: str) -> int:
    """Exact token count using NLI (DeBERTa) tokenizer.

    Lazy-loads tokenizer on first call. Falls back to approx_tokens if
    tokenizer unavailable.
    """
    global _nli_tokenizer
    if _nli_tokenizer is None:
        try:
            from backend.models import get_nli_model
            _, _nli_tokenizer = get_nli_model()
        except (ImportError, OSError, RuntimeError):
            return approx_tokens(text)
    return len(_nli_tokenizer.encode(text, add_special_tokens=False))


def truncate_to_tokens(text: str, max_tokens: int, tokenizer) -> str:
    """Truncate text to fit within a token budget."""
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return text
    return tokenizer.decode(ids[:max_tokens])
