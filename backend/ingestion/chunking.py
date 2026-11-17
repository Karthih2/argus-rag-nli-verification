"""Chunking: merge paragraphs per section, split tables, and build chunk records for MongoDB."""

from dataclasses import replace

from backend.common.ids import chunk_id
from backend.common.numbers import parse_numbers
from backend.common.text import nli_token_count, normalise, quote_spans
from backend.config import settings
from backend.ingestion.elements import Element
from backend.ingestion.tables import table_to_chunks

MERGEABLE = {"text", "list"}


def chunk_elements(elements: list[Element], document_id: str, doc_title: str) -> list[dict]:
    """Turn parsed elements into chunk records (without dataset/document ids or embeddings)."""
    units = []
    for el in elements:
        if el.is_searchable:
            units.extend(table_to_chunks(el) if el.element_type == "table" else [el])
    merged = merge_paragraphs(units, settings.CHUNK_MAX_TOKENS)
    records = [_record(el, document_id, doc_title) for el in merged]
    records = [r for r in records if r["text"]]
    for seq, r in enumerate(records):
        r["seq"] = seq
    return records


def merge_paragraphs(elements: list[Element], max_tokens: int) -> list[Element]:
    """Merge neighbouring text/list items on the same page and under the same heading.

    Never merges across a heading, a page, a table or a figure, and never past max_tokens.
    """
    out: list[Element] = []
    for el in elements:
        prev = out[-1] if out else None
        if (
            prev is not None
            and prev.element_type in MERGEABLE
            and el.element_type in MERGEABLE
            and prev.page == el.page
            and prev.heading_path == el.heading_path
            and nli_token_count(prev.text) + nli_token_count(el.text) <= max_tokens
        ):
            out[-1] = replace(prev, element_type="text", text=f"{prev.text}\n{el.text}")
        else:
            out.append(el)
    return out


def _record(el: Element, document_id: str, doc_title: str) -> dict:
    text = normalise(el.text)
    heading = " > ".join(el.heading_path)
    caption = el.caption if el.caption and el.caption != text else ""
    embed_parts = [doc_title, heading, caption, text]
    return {
        "_id": chunk_id(document_id, el.element_path),
        "element_type": el.element_type,
        "text": text,
        "embed_text": " | ".join(p for p in embed_parts if p),
        "heading_path": el.heading_path,
        "page": el.page,
        "bbox": el.bbox.as_list() if el.bbox else None,
        "numbers": [
            {"raw": n.raw, "value": n.value, "unit": n.unit, "span": list(n.span)}
            for n in parse_numbers(text)
        ],
        "quotes": quote_spans(text),
    }
