"""Read the fitted calibration (trust.json): NLI temperature, claim thresholds, answer trust model.

trust.json is written offline by `python -m scripts.fit_trust`. Until a value is fitted (or when
its risk target could not be met) the fallback below is used and the UI labels it "fallback".
"""

import json
import logging
from functools import lru_cache

import numpy as np

from backend.config import ROOT_DIR

log = logging.getLogger(__name__)

TRUST_JSON = ROOT_DIR / "backend" / "calibration" / "trust.json"
FALLBACK_THRESHOLDS = {"tau_accept": 0.70, "tau_low": 0.50, "tau_block": 0.70}  # hand-set, used until fitted


@lru_cache(maxsize=1)
def load_trust_json() -> dict | None:
    """trust.json, read once; None if it hasn't been fitted yet."""
    if not TRUST_JSON.exists():
        log.warning("trust.json not found at %s; using fallback values", TRUST_JSON)
        return None
    data = json.loads(TRUST_JSON.read_text(encoding="utf-8"))
    log.info("Loaded trust.json v%s (fitted %s)", data.get("version"), data.get("fit_date"))
    return data


def get_temperature() -> float:
    """NLI temperature (1.0 = unscaled)."""
    data = load_trust_json()
    return float(data.get("temperature", 1.0)) if data else 1.0


def get_nli_thresholds() -> dict:
    """tau_accept, tau_low, tau_block: fitted where the risk target was met, else fallback."""
    fitted = (load_trust_json() or {}).get("nli_thresholds", {})
    out = dict(FALLBACK_THRESHOLDS)
    for key, entry in fitted.items():
        if isinstance(entry, dict) and entry.get("met") and entry.get("value") is not None:
            out[key] = float(entry["value"])
    return out


def predict_trust(features: dict) -> int | None:
    """Trust 0-100 = round(100 x P(answer correct)); None when there is nothing to score."""
    if not features:
        return None
    model = (load_trust_json() or {}).get("trust_model")
    if not model:
        # Not fitted yet: plain average support, clearly labelled "fallback" in the UI.
        return round(100 * features.get("mean_support", 0.0))
    row = np.array([float(features.get(k, 0.0)) for k in model["features"]])
    z = (row - np.array(model["mean"])) / np.array(model["scale"])
    logit = float(z @ np.array(model["coef"]) + model["intercept"])
    return int(round(100 / (1 + np.exp(-logit))))


def calibration_info() -> dict:
    """What the UI shows about the calibration: version, which values are fitted, test metrics."""
    data = load_trust_json()
    if not data:
        return {"fitted": False, "thresholds": FALLBACK_THRESHOLDS, "fallback": list(FALLBACK_THRESHOLDS)}
    fitted = data.get("nli_thresholds", {})
    fallback = [k for k in FALLBACK_THRESHOLDS if not (fitted.get(k) or {}).get("met")]
    return {
        "fitted": True,
        "version": data.get("version"),
        "fit_date": data.get("fit_date"),
        "nli_model": data.get("nli_model"),
        "data_sources": data.get("data_sources"),
        "temperature": data.get("temperature"),
        "thresholds": get_nli_thresholds(),
        "threshold_report": fitted,
        "fallback": fallback,
        "risk": data.get("risk"),
        "metrics": data.get("metrics"),
        "note": data.get("note"),
    }
