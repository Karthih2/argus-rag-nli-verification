"""Build chart data from table-type evidence chunks.

Parses the 'Row N: col = val, ...' text back into a table, then picks
pie/bar/line based on column types. Returns None if the chunk isn't a table
or no chart makes sense.
"""

import re

import pandas as pd

_ROW_RE = re.compile(r"^Row\s+\d+:\s*(.+)$", re.MULTILINE)
_CELL_RE = re.compile(r"([^=,]+?)\s*=\s*([^,]+)")


def chart_from_chunk(chunk: dict) -> dict | None:
    """{'type': 'pie'|'bar'|'line', 'labels': [...], 'series': [...]} or None."""
    if chunk.get("element_type") not in ("table", "table_full"):
        return None
    text = chunk.get("text", "")
    rows = _parse_table_text(text)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if df.empty or len(df.columns) < 2:
        return None
    return _pick_chart(df)


def _parse_table_text(text: str) -> list[dict]:
    """Parse 'Row N: col = val, col = val' lines into list of dicts."""
    rows = []
    for match in _ROW_RE.finditer(text):
        cells = {}
        for cell in _CELL_RE.finditer(match.group(1)):
            cells[cell.group(1).strip()] = cell.group(2).strip()
        if cells:
            rows.append(cells)
    return rows


def _pick_chart(df: pd.DataFrame) -> dict | None:
    """Decide chart type from column types."""
    cols = df.columns.tolist()
    label_col = cols[0]
    numeric_cols = []
    for c in cols[1:]:
        converted = pd.to_numeric(df[c].str.replace(r"[,$%]", "", regex=True), errors="coerce")
        if converted.notna().sum() >= len(df) * 0.5:
            numeric_cols.append((c, converted))

    if not numeric_cols:
        return None

    labels = df[label_col].tolist()

    # Pie: single numeric column whose values look like shares of a whole
    if len(numeric_cols) == 1:
        name, values = numeric_cols[0]
        total = values.sum()
        if total > 0 and all(v >= 0 for v in values.dropna()):
            # Check if values are percentages or shares
            if 90 <= total <= 110 or all(0 <= v <= 1 for v in values.dropna()):
                return {
                    "type": "pie",
                    "labels": labels,
                    "series": [{"name": name, "data": [
                        round(float(v), 2) if pd.notna(v) else 0
                        for v in values
                    ]}],
                }

    # Line: first column looks like years or dates
    is_temporal = _is_temporal(df[label_col])

    chart_type = "line" if is_temporal else "bar"
    return {
        "type": chart_type,
        "labels": labels,
        "series": [
            {"name": name, "data": [round(float(v), 2) if pd.notna(v) else 0 for v in values]}
            for name, values in numeric_cols
        ],
    }


def _is_temporal(series: pd.Series) -> bool:
    """True if the series looks like years or dates."""
    nums = pd.to_numeric(series, errors="coerce")
    if nums.notna().all() and (nums >= 1900).all() and (nums <= 2100).all():
        return True
    try:
        pd.to_datetime(series, format="mixed")
        return True
    except (ValueError, TypeError):
        return False
