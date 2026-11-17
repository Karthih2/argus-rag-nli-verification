"""Cross-encoder reranking of fused candidates."""

from backend.config import settings
from backend.models import rerank_scores


def rerank(question: str, candidates: list[dict], keep: int | None = None) -> list[dict]:
    """Score candidates with the reranker; return the top `keep`, best first, with _rerank_score."""
    scores = rerank_scores(question, [c.get("embed_text") or c.get("text", "") for c in candidates])
    scored = [{**c, "_rerank_score": s} for c, s in zip(candidates, scores)]
    scored.sort(key=lambda c: c["_rerank_score"], reverse=True)
    return scored[: keep or settings.RERANK_KEEP]
