"""Risk-controlled thresholds: Clopper-Pearson bounds with fixed-sequence testing (Learn-then-Test)."""

import numpy as np
from scipy.stats import beta

CONFIDENCE = 0.95
GRID = [round(t, 2) for t in np.arange(0.99, 0.49, -0.01)]  # strict -> loose


def clopper_pearson_upper(errors: int, n: int, confidence: float = CONFIDENCE) -> float:
    """One-sided upper confidence bound on an error rate of errors/n."""
    if n == 0:
        return 1.0
    if errors >= n:
        return 1.0
    return float(beta.ppf(confidence, errors + 1, n - errors))


def fixed_sequence(scores, wrong, risk: float, min_n: int, grid=GRID) -> dict:
    """Loosest threshold t (walking strict -> loose) whose set {score >= t} keeps the bound <= risk.

    `wrong[i]` is 1 when example i counts as an error for this threshold. Thresholds covering
    fewer than min_n examples are skipped (that depends only on scores, not labels); the walk
    stops at the first failure, which keeps the 95% guarantee valid across all thresholds.
    Returns {"value", "met", "n", "errors", "bound"}; value is None when no threshold is met.
    """
    scores, wrong = np.asarray(scores), np.asarray(wrong)
    best = {"value": None, "met": False, "n": 0, "errors": 0, "bound": None}
    for t in grid:
        chosen = scores >= t
        n = int(chosen.sum())
        if n < min_n:
            continue
        errors = int(wrong[chosen].sum())
        bound = clopper_pearson_upper(errors, n)
        if bound > risk:
            break
        best = {"value": t, "met": True, "n": n, "errors": errors, "bound": round(bound, 4)}
    return best


def block_threshold(contra, correct, risk: float, grid=GRID) -> dict:
    """Lowest contradiction threshold t whose share of *correct* claims blocked (contra >= t)
    stays <= risk with 95% confidence. Walks strict -> loose and stops at the first failure."""
    contra, correct = np.asarray(contra), np.asarray(correct).astype(bool)
    n = int(correct.sum())
    best = {"value": None, "met": False, "n": n, "errors": 0, "bound": None}
    if n == 0:
        return best
    for t in grid:
        errors = int((contra[correct] >= t).sum())
        bound = clopper_pearson_upper(errors, n)
        if bound > risk:
            break
        best = {"value": t, "met": True, "n": n, "errors": errors, "bound": round(bound, 4)}
    return best
