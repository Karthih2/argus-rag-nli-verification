"""Tables as evidence: 'row, column = value' text, row-group chunks and a whole-table chunk."""

from dataclasses import replace

from backend.config import settings
from backend.ingestion.elements import Element, TableData


def table_to_text(table: TableData, rows: list[list[str]] | None = None, offset: int = 0) -> str:
    """Caption plus one 'Row N: column = value, ...' line per row."""
    rows = table.rows if rows is None else rows
    lines = [table.caption] if table.caption else []
    for i, row in enumerate(rows):
        cells = [
            f"{table.header[j] if j < len(table.header) else f'col{j}'} = {cell}"
            for j, cell in enumerate(row)
            if cell.strip()
        ]
        if cells:
            lines.append(f"Row {offset + i + 1}: {', '.join(cells)}")
    return "\n".join(lines)


def table_to_chunks(element: Element) -> list[Element]:
    """Row groups with the header repeated; small tables also get one whole-table chunk."""
    table = element.table
    if not table or not table.rows:
        return [element]

    size = settings.TABLE_ROWS_PER_CHUNK
    parts = [
        replace(
            element,
            text=table_to_text(table, table.rows[start : start + size], start),
            element_path=f"{element.element_path}_g{start}",
        )
        for start in range(0, len(table.rows), size)
    ]
    if len(table.rows) <= settings.TABLE_MAX_ROWS_WHOLE and len(parts) > 1:
        parts.append(replace(element, element_type="table_full", element_path=f"{element.element_path}_full"))
    return parts
