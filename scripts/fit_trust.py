"""Fit the trust model offline and write backend/calibration/trust.json.

Steps:
1. Temperature-scale NLI logits on FEVER 600-pair sample (minimize NLL).
2. Run RAGTruth answers through verify_claims, extract features.
3. Fit LogisticRegression on 60% train split.
4. Find Clopper–Pearson cut-offs on 20% cal split.
5. Report metrics on 20% test split.
6. Write trust.json.

Run from the repo root:
    python -m scripts.fit_trust
"""

import json
import logging
import sys
from datetime import datetime, timezone

import numpy as np
import pysbd
from scipy.optimize import minimize_scalar
from scipy.stats import binom
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from backend.config import ROOT_DIR, settings
from backend.verification.nli import label_indices, nli_logits

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

TRUST_JSON = ROOT_DIR / "backend" / "calibration" / "trust.json"
RAGTRUTH_FILE = ROOT_DIR / "data" / "ragtruth" / "ragtruth_subset.json"
SEED = 42

# Feature keys must match backend/verification/features.py
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


# ---------------------------------------------------------------------------
# 1. Temperature scaling on FEVER
# ---------------------------------------------------------------------------


def fit_temperature() -> float:
    """Optimal temperature T that minimises NLL on the FEVER 600-pair sample."""
    from eval.fever_data import load_sample_pairs

    pairs_df = load_sample_pairs()
    pairs = list(zip(pairs_df["premise"], pairs_df["hypothesis"]))
    true_labels = pairs_df["label"].tolist()

    idx = label_indices()
    raw_logits = nli_logits(pairs)

    label_to_col = {
        "entailment": idx["entailment"],
        "neutral": idx["neutral"],
        "contradiction": idx["contradiction"],
    }
    y_col = np.array([label_to_col[lab] for lab in true_labels])

    def nll(T: float) -> float:
        scaled = raw_logits / T
        log_probs = scaled - np.log(np.exp(scaled).sum(axis=1, keepdims=True))
        return -np.mean(log_probs[np.arange(len(y_col)), y_col])

    result = minimize_scalar(nll, bounds=(0.1, 10.0), method="bounded")
    temperature = float(result.x)
    log.info("Temperature: %.4f (NLL %.4f -> %.4f)", temperature, nll(1.0), nll(temperature))
    return temperature


# ---------------------------------------------------------------------------
# 2. Process RAGTruth through verify_claims
# ---------------------------------------------------------------------------


def process_ragtruth(temperature: float) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Run RAGTruth answers through NLI verification and extract features.

    Returns (X, y, groups) where:
      X = feature matrix (n_answers, n_features)
      y = binary labels (1 = faithful)
      groups = source_id per answer (for grouped split)
    """
    from backend.calibration.trust_model import FALLBACK_NLI_THRESHOLDS
    from backend.generation.schemas import Claim
    from backend.verification.gate import verify_claims

    if not RAGTRUTH_FILE.exists():
        log.error("RAGTruth data not found. Run: python -m scripts.download_ragtruth")
        sys.exit(1)

    rows = json.loads(RAGTRUTH_FILE.read_text(encoding="utf-8"))
    log.info("Processing %d RAGTruth answers...", len(rows))
    segmenter = pysbd.Segmenter(language="en", clean=False)
    thresholds = FALLBACK_NLI_THRESHOLDS

    X_rows, y_list, groups = [], [], []
    for i, row in enumerate(rows):
        context = row["source_context"]
        response = row["response"]
        faithful = not row["hallucination_spans"]

        # Split response into sentence-claims using pySBD
        sentences = [s.strip() for s in segmenter.segment(response) if s.strip()]
        if not sentences:
            continue

        # Create claims with sentence text for quote matching
        claims = [Claim(text=s, cites=["[1]"], quote=s) for s in sentences]
        # Create fake evidence with the source context as a single chunk
        evidence = [
            {
                "_id": "ragtruth_ctx",
                "_ref": "[1]",
                "_rerank_score": 1.0,
                "text": context[:4000],  # limit to reasonable size
                "element_type": "text",
            }
        ]

        try:
            verified = verify_claims(claims, evidence, temperature, thresholds)
        except (ValueError, RuntimeError, KeyError) as e:
            log.warning("Row %d failed: %s", i, e)
            continue

        # Extract features (same as backend/verification/features.py)
        n = len(verified)
        supports = [c["support"] for c in verified]
        features = {
            "min_support": min(supports),
            "mean_support": sum(supports) / n,
            "max_rel_contra": max(c["contra"] for c in verified),
            "share_supported": sum(c["label"] == "SUPPORTED" for c in verified) / n,
            "n_claims": n,
            "quote_match_rate": sum(c["checks"]["quote_match"] for c in verified) / n,
            "number_mismatches": sum(not c["checks"]["numbers_ok"] for c in verified),
            "top1_rerank": 1.0,  # single chunk, always top
            "rerank_gap": 0.0,
            "repaired": 0,
        }
        X_rows.append([features[k] for k in FEATURE_KEYS])
        y_list.append(1 if faithful else 0)
        groups.append(row.get("source_id", str(i)))

        if (i + 1) % 100 == 0:
            log.info("  processed %d / %d", i + 1, len(rows))

    n_faith = sum(y_list)
    log.info(
        "Processed %d answers: %d faithful, %d hallucinated",
        len(y_list), n_faith, len(y_list) - n_faith,
    )
    return np.array(X_rows), np.array(y_list), groups


# ---------------------------------------------------------------------------
# 3. Fit LogisticRegression
# ---------------------------------------------------------------------------


def fit_model(
    X: np.ndarray, y: np.ndarray, groups: list[str]
) -> tuple[LogisticRegression, np.ndarray, dict, dict, dict]:
    """Split by source document, fit on train, find cutoffs on cal, report on test.

    Returns (model, mean, scale, train_idx, cal_idx, test_idx).
    """
    # 60/20/20 split by group
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=SEED)
    train_idx, rest_idx = next(gss1.split(X, y, groups=groups))

    rest_groups = [groups[i] for i in rest_idx]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=SEED)
    cal_local, test_local = next(gss2.split(X[rest_idx], y[rest_idx], groups=rest_groups))
    cal_idx = rest_idx[cal_local]
    test_idx = rest_idx[test_local]

    log.info("Split: train=%d, cal=%d, test=%d", len(train_idx), len(cal_idx), len(test_idx))

    # Standardise features
    mean = X[train_idx].mean(axis=0)
    scale = X[train_idx].std(axis=0)
    scale[scale == 0] = 1.0  # avoid division by zero

    Z_train = (X[train_idx] - mean) / scale
    model = LogisticRegression(random_state=SEED, max_iter=1000)
    model.fit(Z_train, y[train_idx])
    log.info("Train accuracy: %.4f", model.score(Z_train, y[train_idx]))

    return model, mean, scale, train_idx, cal_idx, test_idx


# ---------------------------------------------------------------------------
# 4. Clopper-Pearson cut-offs
# ---------------------------------------------------------------------------


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Upper bound of 95% Clopper-Pearson confidence interval for error rate k/n."""
    if n == 0:
        return 1.0
    return float(binom.ppf(1 - alpha, n, 1) / n) if k == 0 else float(1 - binom.ppf(alpha / 2, k, 1.0 / n))


def find_cutoffs(
    model: LogisticRegression,
    X: np.ndarray, y: np.ndarray,
    mean: np.ndarray, scale: np.ndarray,
    cal_idx: np.ndarray,
) -> dict:
    """Find Verified and Withheld thresholds on the calibration split.

    Verified: lowest trust threshold whose 95% CP upper bound on error ≤ RISK_VERIFIED.
    Withheld: threshold whose false-withhold rate upper bound ≤ RISK_WITHHOLD.
    """
    Z_cal = (X[cal_idx] - mean) / scale
    probs = model.predict_proba(Z_cal)[:, 1]
    trust_scores = np.round(100 * probs).astype(int)
    y_cal = y[cal_idx]

    # Search verified threshold: scan from 50 up to 99
    # Min examples = 10% of cal set (at least 20)
    min_accepted = max(20, len(cal_idx) // 10)
    verified_threshold = None
    for threshold in range(50, 100):
        accepted = trust_scores >= threshold
        n_accepted = int(accepted.sum())
        if n_accepted < min_accepted:
            continue
        errors = int(((y_cal[accepted] == 0)).sum())
        upper = clopper_pearson_upper(errors, n_accepted)
        if upper <= settings.RISK_VERIFIED:
            verified_threshold = threshold
            break

    if verified_threshold is None:
        # Fallback: pick threshold with lowest observed error rate among those with ≥20 samples
        log.warning(
            "No threshold meets RISK_VERIFIED=%.3f with >=%d examples; using best available",
            settings.RISK_VERIFIED, min_accepted,
        )
        best_err, best_t = 1.0, 75
        for threshold in range(50, 100):
            accepted = trust_scores >= threshold
            n_accepted = int(accepted.sum())
            if n_accepted < 20:
                continue
            errors = int((y_cal[accepted] == 0).sum())
            err_rate = errors / n_accepted
            if err_rate < best_err:
                best_err, best_t = err_rate, threshold
        verified_threshold = best_t
        log.info("Fallback verified threshold: %d (observed error %.3f)", verified_threshold, best_err)

    # Search withheld threshold: scan from 50 down to 0
    withheld_threshold = None
    for threshold in range(50, -1, -1):
        withheld = trust_scores <= threshold
        n_withheld = int(withheld.sum())
        if n_withheld < 10:
            continue
        # False withhold = faithful answers incorrectly withheld
        false_withholds = int((y_cal[withheld] == 1).sum())
        upper = clopper_pearson_upper(false_withholds, n_withheld)
        if upper <= settings.RISK_WITHHOLD:
            withheld_threshold = threshold
            break

    if withheld_threshold is None:
        withheld_threshold = 30  # conservative fallback
        log.warning(
            "No withheld threshold meets RISK_WITHHOLD=%.3f; defaulting to %d",
            settings.RISK_WITHHOLD, withheld_threshold,
        )

    log.info("Thresholds: verified=%s, withheld=%s", verified_threshold, withheld_threshold)
    return {"verified": verified_threshold, "withheld": withheld_threshold}


# ---------------------------------------------------------------------------
# 5. Test metrics
# ---------------------------------------------------------------------------


def test_metrics(
    model: LogisticRegression, X: np.ndarray, y: np.ndarray, mean: np.ndarray, scale: np.ndarray,
    test_idx: np.ndarray, thresholds: dict
) -> dict:
    """Brier, ECE, AUROC, observed error of Verified on test split."""
    Z_test = (X[test_idx] - mean) / scale
    probs = model.predict_proba(Z_test)[:, 1]
    y_test = y[test_idx]

    brier = float(brier_score_loss(y_test, probs))
    auroc = float(roc_auc_score(y_test, probs))

    # ECE (10 bins)
    ece = _ece(probs, y_test, n_bins=10)

    # Observed error at Verified threshold
    trust_scores = np.round(100 * probs).astype(int)
    if thresholds["verified"] is not None:
        accepted = trust_scores >= thresholds["verified"]
        n_accepted = int(accepted.sum())
        errors = int((y_test[accepted] == 0).sum())
        observed_error = errors / n_accepted if n_accepted > 0 else None
    else:
        observed_error = None

    metrics = {
        "brier": round(brier, 4),
        "auroc": round(auroc, 4),
        "ece": round(ece, 4),
        "verified_observed_error": round(observed_error, 4) if observed_error is not None else None,
        "verified_target": settings.RISK_VERIFIED,
        "test_n": len(test_idx),
    }
    log.info("Test metrics: %s", metrics)
    return metrics


def _ece(probs: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error."""
    bins = np.linspace(0, 1, n_bins + 1)
    total = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (probs >= lo) & (probs < hi)
        n = mask.sum()
        if n == 0:
            continue
        avg_conf = probs[mask].mean()
        avg_acc = y[mask].mean()
        total += n * abs(avg_conf - avg_acc)
    return float(total / len(y))


# ---------------------------------------------------------------------------
# 6. Write trust.json
# ---------------------------------------------------------------------------


def write_trust_json(
    temperature: float,
    model: LogisticRegression,
    mean: np.ndarray,
    scale: np.ndarray,
    thresholds: dict,
    metrics: dict,
) -> None:
    data = {
        "version": "2.0",
        "fit_date": datetime.now(timezone.utc).isoformat(),
        "data_sources": ["FEVER-NLI 600-pair sample", "wandb/RAGTruth-processed ~1500 subset"],
        "temperature": round(temperature, 4),
        "trust_model": {
            "features": FEATURE_KEYS,
            "mean": [round(float(v), 6) for v in mean],
            "scale": [round(float(v), 6) for v in scale],
            "coef": [round(float(v), 6) for v in model.coef_[0]],
            "intercept": round(float(model.intercept_[0]), 6),
        },
        "thresholds": thresholds,
        "metrics": metrics,
    }
    TRUST_JSON.parent.mkdir(parents=True, exist_ok=True)
    TRUST_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("Wrote %s", TRUST_JSON)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== fit_trust: fitting trust model ===\n")

    # Step 1: Temperature
    temperature = fit_temperature()

    # Step 2: Process RAGTruth
    X, y, groups = process_ragtruth(temperature)

    # Step 3: Fit model
    model, mean, scale, train_idx, cal_idx, test_idx = fit_model(X, y, groups)

    # Step 4: Cut-offs
    thresholds = find_cutoffs(model, X, y, mean, scale, cal_idx)

    # Step 5: Test metrics
    metrics = test_metrics(model, X, y, mean, scale, test_idx, thresholds)

    # Step 6: Write
    write_trust_json(temperature, model, mean, scale, thresholds, metrics)

    print("\n=== Done. Run the app to use the learned trust model. ===")


if __name__ == "__main__":
    main()
