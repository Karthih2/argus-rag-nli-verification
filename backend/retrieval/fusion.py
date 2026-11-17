"""Reciprocal Rank Fusion of ranked result lists."""

from backend.config import settings


def rrf_fuse(*ranked_lists: list[dict], k: int | None = None, limit: int | None = None) -> list[dict]:
    """Fuse ranked lists of chunks by RRF score (sum of 1 / (k + rank)). Returns the top `limit`."""
    k = k or settings.RRF_K
    limit = limit or settings.RETRIEVE_LIMIT
    scores: dict[str, float] = {}
    by_id: dict[str, dict] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk["_id"]] = scores.get(chunk["_id"], 0.0) + 1.0 / (k + rank)
            by_id.setdefault(chunk["_id"], chunk)
    top = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [{**by_id[cid], "_rrf_score": scores[cid]} for cid in top]
