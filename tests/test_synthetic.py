import random

from backend.calibration.synthetic import swap_entity, swap_number


def test_swap_number_changes_only_the_number():
    out = swap_number("The station hosted 3,285 experiments in 2023.", random.Random(1))
    assert out and out != "The station hosted 3,285 experiments in 2023."
    assert out.startswith("The station hosted ") and "experiments" in out


def test_swap_entity_uses_pool():
    out = swap_entity("Records are kept by NASA headquarters.", random.Random(0), ["ESA", "NASA"])
    assert out == "Records are kept by ESA headquarters."


def test_no_entity_no_mutation():
    assert swap_entity("records are kept.", random.Random(0), ["ESA"]) is None


def test_ids_are_unique_per_document():
    from backend.common.ids import chunk_id

    assert chunk_id("doc_a", "text_1_0") != chunk_id("doc_b", "text_1_0")
