"""Answer-level features: the trust model's inputs, used live and when fitting (one home)."""

from backend.retrieval.context import citable
from backend.verification.aggregate import SUPPORTED

# Inputs of the trust model. Only features that mean the same thing in the fitting data
# (RAGTruth: no quotes, no retrieval) and in live answers.
TRUST_FEATURES = ["min_support", "mean_support", "max_contra", "n_claims", "number_mismatches"]


def extract_features(claims: list[dict], evidence: list[dict] | None = None) -> dict:
    """Trust-model features plus a few display-only ones; {} if there are no claims."""
    if not claims:
        return {}
    n = len(claims)
    supports = [c["support"] for c in claims]
    rerank = [c.get("_rerank_score", 0.0) for c in citable(evidence or [])]
    return {
        "min_support": round(min(supports), 4),
        "mean_support": round(sum(supports) / n, 4),
        "max_contra": round(max(c["contra"] for c in claims), 4),
        "n_claims": n,
        "number_mismatches": sum(not c["checks"]["numbers_ok"] for c in claims),
        "share_supported": round(sum(c["label"] == SUPPORTED for c in claims) / n, 4),
        "quote_match_rate": round(sum(c["checks"]["quote_match"] for c in claims) / n, 4),
        "top1_rerank": round(rerank[0], 4) if rerank else 0.0,
    }


def nli_means(claims: list[dict]) -> dict:
    """Mean entailment / neutral / contradiction over the claims (each claim's split sums to 1)."""
    if not claims:
        return {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
    keys = ("entailment", "neutral", "contradiction")
    return {k: round(sum(c["scores"][k] for c in claims) / len(claims), 4) for k in keys}
