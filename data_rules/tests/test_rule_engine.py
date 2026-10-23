import time

import pytest

from data_rules.schemas import Rule


@pytest.mark.parametrize("category", ["recyclable", "compostable", "landfill"])
def test_every_category_has_a_rule_in_dortmund(engine_rules, category):
    rule = engine_rules.get_rule(category, "DO")
    assert isinstance(rule, Rule)
    assert rule.category == category
    assert rule.region_code == "DO"
    assert rule.bin and rule.reason


def test_compostable_goes_to_the_brown_bin(engine_rules):
    assert "Brown" in engine_rules.get_rule("compostable", "DO").bin


def test_landfill_goes_to_the_grey_bin(engine_rules):
    assert "Grey" in engine_rules.get_rule("landfill", "DO").bin


def test_region_code_is_case_insensitive(engine_rules):
    assert engine_rules.get_rule("landfill", "do") == engine_rules.get_rule("landfill", "DO")


def test_other_regions_give_other_bins(dal, engine_rules):
    dal.add_region("KO", "Koeln")
    dal.set_rule("KO", "compostable", "Green bin", "Organic waste.")
    assert engine_rules.get_rule("compostable", "KO").bin == "Green bin"
    assert engine_rules.get_rule("compostable", "DO").bin != "Green bin"


def test_unknown_region_returns_fallback_and_warns(engine_rules, caplog):
    with caplog.at_level("WARNING"):
        rule = engine_rules.get_rule("landfill", "XX")
    assert rule.bin and rule.reason
    assert "No rule" in caplog.text


def test_unknown_category_raises(engine_rules):
    with pytest.raises(ValueError):
        engine_rules.get_rule("metal", "DO")


def test_lookup_is_fast(engine_rules):
    start = time.perf_counter()
    for _ in range(100):
        engine_rules.get_rule("recyclable", "DO")
    average_ms = (time.perf_counter() - start) / 100 * 1000
    assert average_ms < 50      # non-functional requirement 1
