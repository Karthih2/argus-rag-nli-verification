"""Shared evaluation metrics: calibration error, reliability bins, bootstrap intervals."""

import numpy as np

BINS = 10
SEED = 42


def ece(probs, y, n_bins: int = BINS) -> float:
    """Expected calibration error: weighted gap between confidence and accuracy per bin."""
    probs, y = np.asarray(probs, dtype=float), np.asarray(y, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (probs >= lo) & ((probs < hi) if hi < 1 else (probs <= hi))
        if mask.any():
            total += mask.sum() * abs(probs[mask].mean() - y[mask].mean())
    return float(total / len(y)) if len(y) else 0.0


def reliability(probs, y, n_bins: int = BINS) -> list[dict]:
    """Mean predicted vs observed rate per non-empty bin (for the reliability diagram)."""
    probs, y = np.asarray(probs, dtype=float), np.asarray(y, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (probs >= lo) & ((probs < hi) if hi < 1 else (probs <= hi))
        if mask.any():
            out.append({"predicted": round(float(probs[mask].mean()), 4),
                        "observed": round(float(y[mask].mean()), 4), "n": int(mask.sum())})
    return out


def mean_ci(values) -> dict:
    """Mean with a bootstrap 95% confidence interval."""
    from scipy.stats import bootstrap

    values = np.asarray(values, dtype=float)
    if len(values) < 2 or values.min() == values.max():
        m = float(values.mean()) if len(values) else None
        return {"mean": m, "ci95": [m, m]}
    ci = bootstrap((values,), np.mean, confidence_level=0.95, random_state=SEED, method="percentile")
    return {"mean": round(float(values.mean()), 4),
            "ci95": [round(float(ci.confidence_interval.low), 4), round(float(ci.confidence_interval.high), 4)]}
