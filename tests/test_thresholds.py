from scipy.stats import beta

from backend.calibration.thresholds import block_threshold, clopper_pearson_upper, fixed_sequence


def test_clopper_pearson_matches_beta_quantile():
    assert abs(clopper_pearson_upper(0, 50) - 0.0582) < 1e-3
    assert abs(clopper_pearson_upper(10, 100) - beta.ppf(0.95, 11, 90)) < 1e-9
    assert clopper_pearson_upper(0, 0) == 1.0 and clopper_pearson_upper(5, 5) == 1.0


def test_fixed_sequence_stops_at_first_failure():
    # 300 claims with support 0.95 and no errors, then 300 at 0.6 that are all wrong.
    scores = [0.95] * 300 + [0.6] * 300
    wrong = [0] * 300 + [1] * 300
    res = fixed_sequence(scores, wrong, risk=0.05, min_n=100)
    assert res["met"] and res["value"] > 0.6 and res["errors"] == 0


def test_fixed_sequence_reports_unmet_target():
    res = fixed_sequence([0.9] * 200, [1] * 200, risk=0.05, min_n=100)
    assert not res["met"] and res["value"] is None


def test_block_threshold_bounds_false_blocks():
    contra = [0.99] * 50 + [0.05] * 950
    correct = [False] * 50 + [True] * 950
    res = block_threshold(contra, correct, risk=0.02)
    assert res["met"] and res["errors"] == 0
