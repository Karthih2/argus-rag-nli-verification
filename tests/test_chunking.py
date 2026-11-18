import pytest

from backend.common.text import approx_tokens
from backend.ingestion import chunking, tables
from backend.ingestion.chunking import chunk_elements, merge_paragraphs
from backend.ingestion.elements import Element, TableData
from backend.ingestion.tables import table_to_chunks, table_to_text


@pytest.fixture(autouse=True)
def fixed_token_count(monkeypatch):
    """Count tokens as characters / 4 so the tests don't load the NLI tokenizer (no models in unit tests)."""
    monkeypatch.setattr(chunking, "nli_token_count", approx_tokens)
    monkeypatch.setattr(tables, "nli_token_count", approx_tokens)


def el(kind, text, page=1, heading=("A",), path="p"):
    return Element(kind, text, page, heading_path=list(heading), element_path=path)


def test_merge_stays_inside_section_and_page():
    parts = [
        el("text", "one", path="1"),
        el("list", "two", path="2"),
        el("text", "three", heading=("B",), path="3"),
        el("text", "four", page=2, heading=("B",), path="4"),
    ]
    merged = merge_paragraphs(parts, max_tokens=320)
    assert [m.text for m in merged] == ["one\ntwo", "three", "four"]


def test_merge_respects_token_budget():
    parts = [el("text", "x" * 800, path="1"), el("text", "y" * 800, path="2")]
    assert len(merge_paragraphs(parts, max_tokens=320)) == 2


def test_table_rows_written_as_facts_with_header():
    t = TableData(header=["Type", "Retention"], rows=[["Complaints", "7 years"]], caption="Table 2")
    assert table_to_text(t) == "Table 2\nRow 1: Type = Complaints, Retention = 7 years"


def test_small_multi_group_table_gets_whole_table_chunk():
    t = TableData(header=["n"], rows=[[str(i)] for i in range(7)])
    parts = table_to_chunks(Element("table", "", 3, table=t, element_path="t"))
    assert [p.element_type for p in parts] == ["table", "table", "table_full"]


def test_records_skip_toc_and_use_figure_captions():
    els = [
        el("toc", "Contents 1"),
        el("text", "Body", path="b"),
        Element("figure", "Figure 3. Crew at the rack", 2, caption="Figure 3. Crew at the rack", element_path="f"),
        Element("figure", "", 2, element_path="g"),  # no caption: nothing to search
    ]
    recs = chunk_elements(els, "doc_1", "Doc")
    assert [r["element_type"] for r in recs] == ["text", "figure"]
    assert "Crew at the rack" in recs[1]["embed_text"]
    assert [r["seq"] for r in recs] == [0, 1]
