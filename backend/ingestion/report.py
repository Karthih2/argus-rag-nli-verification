"""Extraction report per document (spec 5.8): what was found, and pages that produced nothing."""

from collections import Counter

from backend.ingestion.elements import ParseResult


def build_report(result: ParseResult, chunks: list[dict]) -> dict:
    """Stats stored on the document and shown in the UI. Also fills page.chunks."""
    per_page = Counter(c["page"] for c in chunks)
    for page in result.pages:
        page.chunks = per_page.get(page.n, 0)

    kinds = Counter(el.element_type for el in result.elements)
    images = Counter(el.image_kind for el in result.elements if el.element_type == "figure")
    return {
        "chunks": len(chunks),
        "tables": kinds["table"],
        "charts": images["chart"],
        "photos": images["photo"],
        "kpis": kinds["kpi"],
        "quotes": sum(len(c["quotes"]) for c in chunks),
        "ocr_pages": 0,  # Docling doesn't report which pages it OCR'd
        "pages_by_kind": dict(Counter(p.kind for p in result.pages)),
        "empty_pages": [p.n for p in result.pages if not p.chunks and p.kind not in ("blank", "toc")],
    }
