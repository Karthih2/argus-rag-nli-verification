from backend.verification.aggregate import count_labels, decide_answer, label_claim

T = {"tau_accept": 0.8, "tau_low": 0.6, "tau_block": 0.7}


def label(**kw):
    args = {
        "support": 0.9,
        "contra": 0.0,
        "quote_found": True,
        "quotations_ok": True,
        "numbers_ok": True,
        **kw,
    }
    return label_claim(**args, thresholds=T)


def test_rules_in_order():
    assert label() == "SUPPORTED"
    assert label(contra=0.75) == "CONTRADICTED"
    assert label(quotations_ok=False) == "CONTRADICTED"
    assert label(numbers_ok=False) == "UNVERIFIED"
    assert label(quote_found=False) == "WEAKLY_SUPPORTED"
    assert label(support=0.65) == "WEAKLY_SUPPORTED"
    assert label(support=0.3) == "UNVERIFIED"


def test_decisions():
    assert decide_answer([], True) == "NO_SUPPORT"
    assert decide_answer(["SUPPORTED", "CONTRADICTED"], False) == "BLOCK"
    assert decide_answer(["SUPPORTED"], False) == "ACCEPT"
    assert decide_answer(["SUPPORTED", "WEAKLY_SUPPORTED"], False) == "ACCEPT_LOW_CONFIDENCE"
    assert decide_answer(["SUPPORTED", "UNVERIFIED"], False) == "WARN"


def test_count_labels():
    counts = count_labels([{"label": "SUPPORTED"}, {"label": "UNVERIFIED"}])
    assert counts == {"supported": 1, "weak": 0, "unverified": 1, "contradicted": 0}
