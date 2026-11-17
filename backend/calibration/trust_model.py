"""Trust model: read learned params from trust.json, predict P(faithful) for one answer.

The JSON is fitted offline by scripts/fit_trust.py and contains:
  - temperature: NLI temperature scalar
  - trust_model: {mean, scale, coef, intercept} for logistic regression
  - thresholds: {verified, withheld} trust score cut-offs
  - metrics: test-split quality numbers
  - version, fit_date, data_sources
"""

import json
import logging
from functools import lru_cache

import numpy as np

from backend.config import ROOT_DIR

log = logging.getLogger(__name__)

TRUST_JSON = ROOT_DIR / "backend" / "calibration" / "trust.json"

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

# Fallback thresholds before trust.json exists
FALLBACK_NLI_THRESHOLDS = {
    "tau_accept": 0.75,
    "tau_low": 0.60,
    "tau_block": 0.75,
    "tau_rel": 0.0,
}


@lru_cache(maxsize=1)
def load_trust_json() -> dict | None:
    """Load trust.json once; None if not yet fitted."""
    if not TRUST_JSON.exists():
        log.warning("trust.json not found at %s — using fallback values", TRUST_JSON)
        return None
    data = json.loads(TRUST_JSON.read_text(encoding="utf-8"))
    log.info("Loaded trust.json v%s (fitted %s)", data.get("version"), data.get("fit_date"))
    return data


def get_temperature() -> float:
    """NLI temperature scalar (1.0 = uncalibrated)."""
    data = load_trust_json()
    return data["temperature"] if data else 1.0


def get_nli_thresholds() -> dict:
    """Thresholds for claim-level NLI decisions."""
    data = load_trust_json()
    if data and "nli_thresholds" in data:
        return {**FALLBACK_NLI_THRESHOLDS, **data["nli_thresholds"]}
    return dict(FALLBACK_NLI_THRESHOLDS)


def get_trust_thresholds() -> dict:
    """Answer-level trust score cut-offs: verified, withheld."""
    data = load_trust_json()
    if data and "thresholds" in data:
        return data["thresholds"]
    return {"verified": 75, "withheld": None}


def predict_trust(features: dict) -> int:
    """Trust score 0-100 for one answer. Fallback heuristic before trust.json exists."""
    if not features:
        return 0
    data = load_trust_json()
    if data and "trust_model" in data:
        params = data["trust_model"]
        row = np.array([[float(features.get(k, 0.0)) for k in FEATURE_KEYS]])
        z = (row - np.array(params["mean"])) / np.array(params["scale"])
        prob = 1.0 / (1.0 + np.exp(-(z @ np.array(params["coef"]) + params["intercept"])))
        return int(round(100 * float(prob[0])))
    # Fallback: weighted average of support and share_supported
    return round(100 * (0.6 * features.get("mean_support", 0) + 0.4 * features.get("share_supported", 0)))


def decide_trust(trust: int) -> str:
    """Map trust score to a decision label using learned thresholds.

    Returns: 'Verified', 'Flagged', or 'Withheld'.
    """
    thresholds = get_trust_thresholds()
    if trust >= thresholds.get("verified", 75):
        return "Verified"
    if thresholds.get("withheld") is not None and trust <= thresholds["withheld"]:
        return "Withheld"
    return "Flagged"
