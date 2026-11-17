import numpy as np

from backend.calibration.trust_model import ece, fit_trust_model, predict_trust
from backend.verification.features import FEATURE_KEYS


def ex(label, support, source="synthetic"):
    feats = dict.fromkeys(FEATURE_KEYS, 0.0) | {"min_support": support, "mean_support": support}
    return {"label": label, "features": feats, "source": source}


def test_fit_and_predict_separates_classes():
    rng = np.random.default_rng(0)
    train = [ex(1, rng.uniform(0.7, 1)) for _ in range(40)] + [ex(0, rng.uniform(0, 0.4)) for _ in range(40)]
    model = fit_trust_model(train, train[:10] + train[-10:])
    assert model is not None and model["heldout"]["brier"] < 0.1
    assert predict_trust(model["params"], ex(1, 0.95)["features"]) > 80
    assert predict_trust(model["params"], ex(0, 0.05)["features"]) < 20


def test_too_few_examples_keeps_previous():
    assert fit_trust_model([ex(1, 0.9)] * 5 + [ex(0, 0.1)] * 5, []) is None


def test_fallback_trust_and_ece():
    assert predict_trust(None, {"mean_support": 1.0, "share_supported": 1.0}) == 100
    assert ece(np.array([1, 0]), np.array([1.0, 0.0])) == 0.0
