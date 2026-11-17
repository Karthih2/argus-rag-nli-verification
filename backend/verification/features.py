"""Trust-model features for one answer. Used live and for calibration."""

from backend.retrieval.context import citable
from backend.verification.aggregate import SUPPORTED

FEATURE_KEYS = [
    "min_support",
    "mean_support",
    "max_rel_contra",
    "share_supported",
    "n_claims",
    "quote_match_rate",
    "number_mismatches",
    "top1_rerank",
    "rerank_gap",
    "repaired",
]


def extract_features(claims: list[dict], evidence: list[dict], repaired: bool) -> dict:
    """Feature dict (all FEATURE_KEYS) for the trust model; {} if there are no claims."""
    if not claims:
        return {}
    n = len(claims)
    supports = [c["support"] for c in claims]
    rerank = [c.get("_rerank_score", 0.0) for c in citable(evidence)]
    return {
        "min_support": min(supports),
        "mean_support": round(sum(supports) / n, 4),
        "max_rel_contra": max(c["contra"] for c in claims),
        "share_supported": round(sum(c["label"] == SUPPORTED for c in claims) / n, 4),
        "n_claims": n,
        "quote_match_rate": round(sum(c["checks"]["quote_match"] for c in claims) / n, 4),
        "number_mismatches": sum(not c["checks"]["numbers_ok"] for c in claims),
        "top1_rerank": round(rerank[0], 4) if rerank else 0.0,
        "rerank_gap": round(rerank[0] - rerank[1], 4) if len(rerank) > 1 else 0.0,
        "repaired": int(repaired),
    }
