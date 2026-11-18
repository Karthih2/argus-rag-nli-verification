"""Text normalisation and helpers shared by chunking, checks, verification and calibration."""

import re
import unicodedata
from functools import lru_cache

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


@lru_cache(maxsize=1)
def _segmenter():
    import pysbd

    return pysbd.Segmenter(language="en", clean=False, char_span=True)


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """[start, end) of each sentence. Lines (e.g. table rows) are split first, then sentences."""
    spans = []
    for line in re.finditer(r"[^\n]+", text):
        for s in _segmenter().segment(line.group(0)):
            start, end = line.start() + s.start, line.start() + s.end
            if text[start:end].strip():
                spans.append((start, end))
    return spans


def sentences(text: str) -> list[str]:
    """Sentences of a text, stripped."""
    return [text[s:e].strip() for s, e in sentence_spans(text)]


_nli_tokenizer = None


def nli_token_count(text: str) -> int:
    """Exact token count with the NLI (DeBERTa) tokenizer; approx_tokens if it can't be loaded."""
    global _nli_tokenizer
    if _nli_tokenizer is None:
        try:
            from backend.models import get_nli_model

            _, _nli_tokenizer = get_nli_model()
        except (ImportError, OSError, RuntimeError):
            return approx_tokens(text)
    return len(_nli_tokenizer.encode(text, add_special_tokens=False))


def split_passages(text: str, max_tokens: int) -> list[str]:
    """Pack whole sentences into passages of at most max_tokens NLI tokens (for long contexts)."""
    passages, current, used = [], [], 0
    for sent in sentences(text):
        cost = nli_token_count(sent)
        if current and used + cost > max_tokens:
            passages.append(" ".join(current))
            current, used = [], 0
        current.append(sent)
        used += cost
    if current:
        passages.append(" ".join(current))
    return passages
