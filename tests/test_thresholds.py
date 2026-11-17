import numpy as np

from backend.calibration.thresholds import (
    clopper_pearson_upper,
    fit_thresholds,
    tau_accept,
    tau_block,
    tau_rel,
)


def test_clopper_pearson():
    assert clopper_pearson_upper(0, 0) == 1.0
    assert 0.04 < clopper_pearson_upper(0, 60) < 0.05  # rule of three: about 3/n
    assert clopper_pearson_upper(5, 50) > 0.1


def test_tau_accept_stops_at_first_failure():
    # 100 correct answers with high support, then wrong answers just below 0.9.
    support = np.array([0.95] * 100 + [0.85] * 30 + [0.6] * 5)
    labels = np.array([1] * 100 + [0] * 30 + [1] * 5)
    assert tau_accept(support, labels, risk=0.05) == 0.86


def test_tau_accept_none_when_never_safe():
    assert tau_accept(np.array([0.99] * 10), np.array([0] * 10), risk=0.05) is None


def test_tau_block_protects_correct_answers():
    contra = np.array([0.01] * 200 + [0.9] * 20)
    labels = np.array([1] * 200 + [0] * 20)
    assert tau_block(contra, labels, risk=0.02) == 0.5


def test_tau_rel_separates_gold():
    assert 0.3 < tau_rel([0.9, 0.8, 0.7], [0.1, 0.2, 0.3]) <= 0.7


def test_fit_thresholds_reports_guarantee():
    cal = [{"label": 1, "features": {"min_support": 0.95, "max_rel_contra": 0.0}}] * 100
    out = fit_thresholds(cal, {"risk_alpha_accept": 0.05, "risk_alpha_low": 0.15, "risk_false_block": 0.02})
    assert out["tau_accept"] == 0.5 and out["coverage"] == 1.0 and out["accepted_error_ucb"] <= 0.05
