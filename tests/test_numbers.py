from backend.common.numbers import missing_numbers, parse_numbers


def test_parses_units_and_commas():
    nums = parse_numbers("Kept 7 years; 22 percent of 3,285 cases cost $1,200.")
    assert [(n.value, n.unit) for n in nums] == [(7, "year"), (22, "%"), (3285, ""), (1200, "USD")]


def test_missing_numbers_flags_a_swap():
    assert [n.raw for n in missing_numbers("Claim says 2,543 papers", "page 1 says 2,534")] == ["2,543"]


def test_unit_missing_on_one_side_still_matches():
    assert missing_numbers("Destroyed after 7 years", "Retention = Destroy 7 after closure") == []
    assert missing_numbers("22% of crews", "22 percent of crews") == []
