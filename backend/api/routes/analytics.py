"""Analytics from `queries`: totals, decisions per day, trust histogram, latency."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
from fastapi import APIRouter, Query

from backend.calibration.trust_model import load_trust_json
from backend.db.client import queries
from backend.verification.aggregate import DECISIONS

router = APIRouter(tags=["analytics"])
STAGES = ("retrieve", "rerank", "llm", "verify")
TRUST_BINS = 10


@router.get("/analytics")
def analytics(dataset_id: str | None = None, days: int = Query(14, ge=1, le=365)):
    """Everything the analytics page draws, computed from stored queries in the window."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    match = {"ts": {"$gte": since}, **({"dataset_id": dataset_id} if dataset_id else {})}
    rows = list(
        queries().find(match, {"ts": 1, "decision": 1, "trust": 1, "latency_ms": 1, "feedback.value": 1})
    )
    return {
        "days": days,
        "totals": _totals(rows),
        "per_day": _per_day(rows, days),
        "trust_histogram": _trust_hist(rows),
        "latency": _latency(rows, days),
    }


@router.get("/trust-info")
def trust_info():
    """Trust model metadata and test metrics from trust.json (None if not fitted)."""
    data = load_trust_json()
    if not data:
        return {"fitted": False}
    return {
        "fitted": True,
        "version": data.get("version"),
        "fit_date": data.get("fit_date"),
        "temperature": data.get("temperature"),
        "thresholds": data.get("thresholds"),
        "metrics": data.get("metrics"),
        "data_sources": data.get("data_sources"),
    }


def _totals(rows: list[dict]) -> dict:
    trust = [r["trust"] for r in rows if r.get("decision") != "NO_SUPPORT"]
    total_ms = [r["latency_ms"]["total"] for r in rows if r.get("latency_ms")]
    return {
        "questions": len(rows),
        "decisions": {d: sum(r.get("decision") == d for r in rows) for d in DECISIONS},
        "avg_trust": round(float(np.mean(trust))) if trust else None,
        "p50_ms": int(np.percentile(total_ms, 50)) if total_ms else None,
        "p95_ms": int(np.percentile(total_ms, 95)) if total_ms else None,
        "feedback": sum((r.get("feedback") or {}).get("value") is not None for r in rows),
    }


def _day_keys(days: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _per_day(rows: list[dict], days: int) -> list[dict]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        counts[r["ts"][:10]][r.get("decision")] += 1
    return [{"day": d, **{k: counts[d][k] for k in DECISIONS}} for d in _day_keys(days)]


def _trust_hist(rows: list[dict]) -> list[int]:
    bins = [0] * TRUST_BINS
    for r in rows:
        if r.get("decision") != "NO_SUPPORT":
            bins[min(int(r.get("trust", 0)) // 10, TRUST_BINS - 1)] += 1
    return bins


def _latency(rows: list[dict], days: int) -> dict:
    by_day: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.get("latency_ms"):
            by_day[r["ts"][:10]].append(r["latency_ms"]["total"])
    series = [
        {
            "day": d,
            "p50": int(np.percentile(v, 50)) if v else None,
            "p95": int(np.percentile(v, 95)) if v else None,
        }
        for d in _day_keys(days)
        for v in [by_day.get(d, [])]
    ]
    stages = {
        s: [r["latency_ms"][s] for r in rows if r.get("latency_ms", {}).get(s) is not None] for s in STAGES
    }
    return {
        "series": series,
        "stage_median_ms": {s: int(np.median(v)) if v else None for s, v in stages.items()},
    }
