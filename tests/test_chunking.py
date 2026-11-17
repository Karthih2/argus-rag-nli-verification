from backend.ingestion.chunking import chunk_elements, merge_paragraphs
from backend.ingestion.elements import Element, TableData
from backend.ingestion.tables import table_to_chunks, table_to_text


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


def test_records_skip_toc_and_keep_derived_only_figures():
    els = [
        el("toc", "Contents 1"),
        el("text", "Body", path="b"),
        Element("figure", "", 2, derived="A crew member at a rack", element_path="f", asset_id="a_1"),
    ]
    recs = chunk_elements(els, "doc_1", "Doc")
    assert [r["element_type"] for r in recs] == ["text", "figure"]
    assert recs[1]["asset_id"] == "a_1" and "crew member" in recs[1]["embed_text"]
    assert [r["seq"] for r in recs] == [0, 1]
