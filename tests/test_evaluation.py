import pytest


@pytest.mark.parametrize("answer", ["8.5 kg", "0.8 kg", "-8 kg", "18 kg"])
def test_numeric_reference_does_not_credit_a_different_value(answer):
    from scripts.evaluate import contains_reference

    assert not contains_reference(answer, ["8"])


@pytest.mark.parametrize("answer", ["8 kg", "8.0 kg", "Ağırlık 8kg."])
def test_equivalent_whole_numeric_reference_is_accepted(answer):
    from scripts.evaluate import contains_reference

    assert contains_reference(answer, ["8"])
