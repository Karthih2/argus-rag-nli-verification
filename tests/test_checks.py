from backend.verification.checks import find_quote, number_problems, quotations_ok

SOURCE = 'Records of complaints: Destroy 7 years after case is closed. The policy says "integrity first".'


def test_quote_found_with_span():
    found, score, span = find_quote("Destroy 7 years after case is closed", SOURCE)
    assert found and score > 0.95 and SOURCE[span[0] : span[1]].startswith("Destroy")


def test_quote_missing():
    assert not find_quote("Destroy 9 decades later", SOURCE)[0]


def test_misquoted_quotation():
    assert quotations_ok('The policy says "integrity first".', SOURCE)
    assert not quotations_ok('The policy says "speed above all".', SOURCE)


def test_number_problem_explained():
    assert "9 years" in number_problems("Destroyed after 9 years", SOURCE)
