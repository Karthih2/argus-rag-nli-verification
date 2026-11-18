from backend.calibration import trust_model

MODEL = {"features": ["mean_support", "max_contra"], "mean": [0.5, 0.5], "scale": [0.2, 0.2],
         "coef": [2.0, -2.0], "intercept": 0.0}


def use(monkeypatch, data):
    monkeypatch.setattr(trust_model, "load_trust_json", lambda: data)


def test_no_claims_means_no_trust(monkeypatch):
    use(monkeypatch, {"trust_model": MODEL})
    assert trust_model.predict_trust({}) is None


def test_trust_rises_with_support_and_falls_with_contradiction(monkeypatch):
    use(monkeypatch, {"trust_model": MODEL})
    good = trust_model.predict_trust({"mean_support": 0.95, "max_contra": 0.01})
    bad = trust_model.predict_trust({"mean_support": 0.95, "max_contra": 0.9})
    assert good > 90 > bad


def test_unmet_thresholds_fall_back(monkeypatch):
    use(monkeypatch, {"nli_thresholds": {"tau_accept": {"value": 0.83, "met": True},
                                         "tau_low": {"value": None, "met": False}}})
    t = trust_model.get_nli_thresholds()
    assert t["tau_accept"] == 0.83 and t["tau_low"] == trust_model.FALLBACK_THRESHOLDS["tau_low"]
