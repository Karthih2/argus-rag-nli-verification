from backend.retrieval.context import citable
from backend.retrieval.fusion import rrf_fuse


def test_rrf_rewards_agreement():
    a = [{"_id": "x"}, {"_id": "y"}]
    b = [{"_id": "y"}, {"_id": "z"}]
    assert [c["_id"] for c in rrf_fuse(a, b, k=60, limit=3)] == ["y", "x", "z"]


def test_citable_excludes_neighbours_and_sorts_by_rerank():
    ev = [
        {"_ref": "C1", "_rerank_score": 0.2},
        {"_ref": "N1", "_is_neighbour": True},
        {"_ref": "C2", "_rerank_score": 0.9},
    ]
    assert [c["_ref"] for c in citable(ev)] == ["C2", "C1"]


def test_table_row_groups_are_not_duplicates_but_whole_table_is():
    from backend.retrieval.context import _overlap

    hdr = "Table 2"
    g1 = {"element_type": "table", "text": f"{hdr}\nRow 1: Type = A, Years = 7\nRow 2: Type = B, Years = 6"}
    g2 = {"element_type": "table", "text": f"{hdr}\nRow 3: Type = C, Years = 5\nRow 4: Type = D, Years = 4"}
    full = {"element_type": "table_full", "text": g1["text"] + "\n" + g2["text"].split("\n", 1)[1]}
    assert _overlap(g1, g2) <= 0.5 and _overlap(g1, full) == 1.0
