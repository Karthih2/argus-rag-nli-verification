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
