"""Docling parser: layout, reading order, tables, figures and OCR, as typed elements."""

import logging
from functools import lru_cache
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    DocItemLabel,
    PictureClassificationData,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

from backend.ingestion.elements import BBox, Element, PageInfo, ParseResult, TableData
from backend.ingestion.tables import table_to_text

log = logging.getLogger(__name__)

CHART_CLASSES = {"bar_chart", "line_chart", "pie_chart", "scatter_plot", "flow_chart"}
LOGO_CLASSES = {"logo", "icon", "stamp"}
TEXT_KINDS = {DocItemLabel.FOOTNOTE: "footnote", DocItemLabel.LIST_ITEM: "list"}
SKIP_LABELS = {DocItemLabel.CAPTION, DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER}
TOC_WORDS = ("table of contents", "contents")
PAGE_KIND_ORDER = ("toc", "table", "chart", "photo", "text")


@lru_cache(maxsize=1)
def _converter() -> DocumentConverter:
    """Docling converter, built once."""
    opts = PdfPipelineOptions()
    opts.do_table_structure = True
    opts.table_structure_options.mode = TableFormerMode.ACCURATE
    opts.do_ocr = True
    opts.generate_picture_images = False  # no vision model, no image storage
    opts.do_picture_classification = True
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})


def parse_docling(pdf_path: Path) -> ParseResult:
    """Parse a PDF with Docling into typed elements, page info and outline."""
    doc = _converter().convert(pdf_path).document
    state = _State()
    for item, _level in doc.iterate_items():
        _handle_item(item, doc, state)

    toc_pages = {p for p, kinds in state.page_kinds.items() if "toc" in kinds}
    for el in state.elements:
        if el.page in toc_pages:
            el.element_type = "toc"

    page_count = len(doc.pages)
    return ParseResult(
        elements=state.elements,
        pages=[PageInfo(n, _page_kind(state.page_kinds.get(n, set()))) for n in range(1, page_count + 1)],
        outline=state.outline,
        metadata={"title": state.title, "page_count": page_count},
    )


class _State:
    """Running state while walking the document in reading order."""

    def __init__(self) -> None:
        self.elements: list[Element] = []
        self.page_kinds: dict[int, set[str]] = {}
        self.headings: list[str] = []
        self.outline: list[dict] = []
        self.title = ""

    def add(self, el: Element, page_kind: str) -> None:
        el.heading_path = list(self.headings)
        el.element_path = f"{el.element_type}_{el.page}_{len(self.elements)}"
        self.elements.append(el)
        self.page_kinds.setdefault(el.page, set()).add(page_kind)


def _handle_item(item, doc, state: _State) -> None:
    page, bbox = _location(item, doc)
    if isinstance(item, SectionHeaderItem) or getattr(item, "label", None) == DocItemLabel.TITLE:
        _handle_heading(item, page, state)
    elif isinstance(item, TableItem):
        if item.label == DocItemLabel.DOCUMENT_INDEX:
            state.page_kinds.setdefault(page, set()).add("toc")
            return
        table = _extract_table(item, doc)
        state.add(
            Element("table", table_to_text(table), page, bbox, table=table, caption=table.caption), "table"
        )
    elif isinstance(item, PictureItem):
        _handle_picture(item, doc, page, bbox, state)
    elif isinstance(item, TextItem) and item.label not in SKIP_LABELS and item.text.strip():
        kind = TEXT_KINDS.get(item.label, "text")
        state.add(Element(kind, item.text.strip(), page, bbox), "text")


def _handle_heading(item, page: int, state: _State) -> None:
    text = item.text.strip()
    if not text:
        return
    if item.label == DocItemLabel.TITLE:
        state.title = state.title or text
        return
    level = max(getattr(item, "level", 1), 1)
    state.headings = state.headings[: level - 1] + [text]
    state.outline.append({"level": level, "title": text, "page": page})
    if text.lower() in TOC_WORDS:
        state.page_kinds.setdefault(page, set()).add("toc")


def _handle_picture(item: PictureItem, doc, page: int, bbox: BBox | None, state: _State) -> None:
    top_class = _picture_class(item)
    kind = "logo" if top_class in LOGO_CLASSES else "chart" if top_class in CHART_CLASSES else "photo"
    caption = item.caption_text(doc) or ""
    el = Element(
        "logo" if kind == "logo" else "figure",
        caption,
        page,
        bbox,
        image_kind=kind,
        caption=caption,
    )
    state.add(el, kind)


def _location(item, doc) -> tuple[int, BBox | None]:
    """Page number and bbox normalised to 0-1 with a top-left origin."""
    prov = getattr(item, "prov", None)
    if not prov:
        return 0, None
    p = prov[0]
    page = doc.pages.get(p.page_no)
    if page is None or not page.size.width or not page.size.height:
        return p.page_no, None
    box = p.bbox.to_top_left_origin(page.size.height).normalized(page.size)
    return p.page_no, BBox(box.l, box.t, box.r, box.b)


def _picture_class(item: PictureItem) -> str:
    """Top predicted class."""
    meta_cls = getattr(getattr(item, "meta", None), "classification", None)
    if meta_cls is not None:
        return meta_cls.get_main_prediction().class_name
    for ann in getattr(item, "annotations", []):
        if isinstance(ann, PictureClassificationData) and ann.predicted_classes:
            return ann.predicted_classes[0].class_name
    return "photo"


def _extract_table(item: TableItem, doc) -> TableData:
    df = item.export_to_dataframe(doc=doc)
    return TableData(
        header=[str(c) for c in df.columns],
        rows=[[str(cell) for cell in row] for row in df.values.tolist()],
        caption=item.caption_text(doc) or "",
    )


def _page_kind(kinds: set[str]) -> str:
    return next((k for k in PAGE_KIND_ORDER if k in kinds), "blank")
