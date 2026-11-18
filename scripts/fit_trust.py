"""Fit the calibration offline and write backend/calibration/trust.json.

1. Temperature for the NLI probabilities, on the FEVER-NLI 600-pair sample.
2. RAGTruth answers through the live verifier (eval/ragtruth.py); split 60/20/20 by source context.
3. Claim thresholds on the cal split, with a 95% Clopper-Pearson guarantee (fixed-sequence testing):
   tau_accept (RISK_VERIFIED), tau_low (RISK_LOW), tau_block (RISK_WITHHOLD).
4. Trust model: logistic regression on answer features (fit split), no class weights.
5. Test-split metrics, then trust.json.

Run from the repo root (NLI over ~1,500 answers; about 30-60 min on CPU, cached afterwards):
    python -m scripts.fit_trust [--limit N] [--refresh]
"""

import argparse
import json
import logging
from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import brier_score_loss, roc_auc_score

from backend.calibration.temperature import fit_temperature
from backend.calibration.thresholds import block_threshold, clopper_pearson_upper, fixed_sequence
from backend.calibration.trust_model import TRUST_JSON
from backend.config import settings
from backend.verification.features import TRUST_FEATURES
from backend.verification.nli import label_indices, nli_logits
from eval.fever_data import load_sample_pairs
from eval.metrics import ece, reliability
from eval.ragtruth import split_groups, verified_examples

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
SEED = 42


def nli_temperature() -> float:
    """T minimising NLL of the FEVER gold labels under softmax(logits / T)."""
    pairs = load_sample_pairs()
    idx = label_indices()
    labels = np.array([idx[lab] for lab in pairs["label"]])
    return fit_temperature(nli_logits(list(zip(pairs["premise"], pairs["hypothesis"]))), labels)


def claim_arrays(examples: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """support, contra, faithful for every claim in the examples."""
    claims = [c for e in examples for c in e["claims"]]
    return (np.array([c["support"] for c in claims]), np.array([c["contra"] for c in claims]),
            np.array([c["faithful"] for c in claims], dtype=bool))


def fit_thresholds(cal: list[dict]) -> dict:
    support, contra, faithful = claim_arrays(cal)
    wrong = (~faithful).astype(int)
    return {
        "tau_accept": fixed_sequence(support, wrong, settings.RISK_VERIFIED, settings.CAL_MIN_EXAMPLES),
        "tau_low": fixed_sequence(support, wrong, settings.RISK_LOW, settings.CAL_MIN_EXAMPLES),
        "tau_block": block_threshold(contra, faithful, settings.RISK_WITHHOLD),
    }


def answer_matrix(examples: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    X = np.array([[e["features"][k] for k in TRUST_FEATURES] for e in examples], dtype=float)
    return X, np.array([e["faithful"] for e in examples], dtype=int)


def fit_trust_model(fit: list[dict]) -> dict:
    """Standardise, then L2 logistic regression with C chosen by 5-fold CV (log-loss)."""
    X, y = answer_matrix(fit)
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1.0
    model = LogisticRegressionCV(Cs=10, cv=5, scoring="neg_log_loss", max_iter=2000, random_state=SEED)
    model.fit((X - mean) / scale, y)
    coef = dict(zip(TRUST_FEATURES, model.coef_[0]))
    if coef["mean_support"] < 0 or coef["max_contra"] > 0:
        log.warning("Unexpected coefficient signs (support should raise trust, contradiction lower it): %s", coef)
    return {"features": TRUST_FEATURES, "mean": mean.round(6).tolist(), "scale": scale.round(6).tolist(),
            "coef": model.coef_[0].round(6).tolist(), "intercept": round(float(model.intercept_[0]), 6),
            "C": float(model.C_[0])}


def predict(model: dict, X: np.ndarray) -> np.ndarray:
    z = (X - np.array(model["mean"])) / np.array(model["scale"])
    return 1 / (1 + np.exp(-(z @ np.array(model["coef"]) + model["intercept"])))


def test_metrics(test: list[dict], model: dict, thresholds: dict) -> dict:
    """Trust-model quality and what the fitted claim threshold does on unseen contexts."""
    X, y = answer_matrix(test)
    p = predict(model, X)
    support, _, faithful = claim_arrays(test)
    out = {"test_answers": len(test), "test_claims": len(support), "brier": round(float(brier_score_loss(y, p)), 4),
           "ece": round(ece(p, y), 4), "auroc": round(float(roc_auc_score(y, p)), 4), "reliability": reliability(p, y)}
    tau = thresholds["tau_accept"]["value"]
    if tau is not None:
        accepted = support >= tau
        errors, n = int((~faithful[accepted]).sum()), int(accepted.sum())
        out.update(claim_accept_error=round(errors / n, 4) if n else None, claim_accept_upper=round(
            clopper_pearson_upper(errors, n), 4), claim_coverage=round(n / len(support), 4))
    return out


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--limit", type=int, help="use only the first N RAGTruth answers (quick test)")
    args.add_argument("--refresh", action="store_true", help="re-run NLI even if cached")
    opts = args.parse_args()

    temperature = nli_temperature()
    log.info("Temperature T = %.4f", temperature)
    splits = split_groups(verified_examples(temperature, opts.limit, opts.refresh))
    log.info("Split: fit=%d cal=%d test=%d answers", *(len(splits[k]) for k in ("fit", "cal", "test")))

    thresholds = fit_thresholds(splits["cal"])
    model = fit_trust_model(splits["fit"])
    metrics = test_metrics(splits["test"], model, thresholds)
    data = {
        "version": datetime.now(timezone.utc).strftime("%Y.%m.%d"),
        "fit_date": datetime.now(timezone.utc).isoformat(),
        "nli_model": settings.NLI_MODEL_NAME,
        "data_sources": ["FEVER-NLI 600-pair sample (temperature)",
                         f"wandb/RAGTruth-processed subset, {sum(len(v) for v in splits.values())} answers"],
        "temperature": temperature,
        "risk": {"verified": settings.RISK_VERIFIED, "low": settings.RISK_LOW, "withhold": settings.RISK_WITHHOLD},
        "nli_thresholds": thresholds,
        "trust_model": model,
        "metrics": metrics,
    }
    TRUST_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {TRUST_JSON}")
    summary = ", ".join(f"{k}={v['value']} (met={v['met']})" for k, v in thresholds.items())
    print(f"T={temperature}  thresholds: {summary}")
    print("test metrics:", {k: v for k, v in metrics.items() if k != "reliability"})
    missed = [k for k, v in thresholds.items() if not v["met"]]
    if missed:
        print("\n" + "!" * 70)
        print(f"WARNING: risk target not met for {missed}. The app uses the fallback value for these")
        print("and labels them 'fallback'. More calibration data or a stronger NLI model may help.")
        print("!" * 70)


if __name__ == "__main__":
    main()
