"""The error class of Data & Rules, and that the code really raises it."""
import pytest

from data_rules import DataRulesError
from data_rules.seed import load_rule_files


def test_older_code_can_still_catch_a_value_error():
    assert issubclass(DataRulesError, ValueError)


def test_unknown_category_raises_the_error(dal):
    with pytest.raises(DataRulesError, match="category"):
        dal.save_result("bottle", "unknown", 0.5, "DO")


def test_confidence_out_of_range_raises_the_error(dal):
    with pytest.raises(DataRulesError, match="confidence"):
        dal.save_result("bottle", "recyclable", 1.5, "DO")


def test_rule_engine_raises_the_error(engine_rules):
    with pytest.raises(DataRulesError):
        engine_rules.get_rule("unknown", "DO")


def test_saving_for_an_unknown_region_raises_the_error(dal):
    with pytest.raises(DataRulesError, match="XX"):
        dal.save_result("bottle", "recyclable", 0.5, "XX")


def test_rule_for_an_unknown_region_raises_the_error(dal):
    with pytest.raises(DataRulesError, match="XX"):
        dal.set_rule("XX", "recyclable", "bin", "reason")


def test_rule_file_with_broken_json_names_the_file(tmp_path):
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(DataRulesError, match="broken.json"):
        load_rule_files(tmp_path)
