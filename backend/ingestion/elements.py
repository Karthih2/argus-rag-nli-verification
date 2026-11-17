"""Typed content elements extracted from a document."""

from dataclasses import dataclass, field

NOT_SEARCHABLE = {"toc", "heading", "logo"}


@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def as_list(self) -> list[float]:
        return [round(v, 4) for v in (self.x0, self.y0, self.x1, self.y1)]


@dataclass
class TableData:
    header: list[str]
    rows: list[list[str]]
    caption: str = ""


@dataclass
class Element:
    """One extracted content element from a document."""

    element_type: str  # text, list, footnote, table, table_full, figure, logo, toc
    text: str = ""
    page: int = 0
    bbox: BBox | None = None
    heading_path: list[str] = field(default_factory=list)
    table: TableData | None = None
    image_kind: str = ""  # chart, photo, logo
    caption: str = ""
    element_path: str = ""  # unique path within the document, used for chunk_id

    @property
    def is_searchable(self) -> bool:
        return self.element_type not in NOT_SEARCHABLE


@dataclass
class PageInfo:
    n: int
    kind: str  # text, table, chart, photo, toc, blank
    chunks: int = 0


@dataclass
class ParseResult:
    """Full parse output from a document."""

    elements: list[Element] = field(default_factory=list)
    pages: list[PageInfo] = field(default_factory=list)
    outline: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
