"""The error classes of Data & Rules, and that the code really raises them."""
import pytest

from data_rules import (
    DatabaseError,
    DataRulesError,
    InvalidDataError,
    NoRuleFilesError,
    RuleFileError,
    UnknownRegionError,
)
from data_rules.models import Base
from data_rules.seed import load_rule_files


@pytest.mark.parametrize(
    "error",
    [InvalidDataError, UnknownRegionError, RuleFileError, NoRuleFilesError, DatabaseError],
)
def test_every_error_can_be_caught_as_data_rules_error(error):
    assert issubclass(error, DataRulesError)


@pytest.mark.parametrize("error", [InvalidDataError, UnknownRegionError, RuleFileError])
def test_older_code_can_still_catch_a_value_error(error):
    assert issubclass(error, ValueError)


def test_older_code_can_still_catch_a_missing_rules_folder():
    assert issubclass(NoRuleFilesError, FileNotFoundError)


def test_unknown_category_raises_invalid_data_error(dal):
    with pytest.raises(InvalidDataError, match="category"):
        dal.save_result("bottle", "unknown", 0.5, "DO")


def test_confidence_out_of_range_raises_invalid_data_error(dal):
    with pytest.raises(InvalidDataError, match="confidence"):
        dal.save_result("bottle", "recyclable", 1.5, "DO")


def test_rule_engine_raises_invalid_data_error(engine_rules):
    with pytest.raises(InvalidDataError):
        engine_rules.get_rule("unknown", "DO")


def test_saving_for_an_unknown_region_raises_unknown_region_error(dal):
    with pytest.raises(UnknownRegionError, match="XX"):
        dal.save_result("bottle", "recyclable", 0.5, "XX")


def test_rule_for_an_unknown_region_raises_unknown_region_error(dal):
    with pytest.raises(UnknownRegionError, match="XX"):
        dal.set_rule("XX", "recyclable", "bin", "reason")


def test_empty_rules_folder_raises_no_rule_files_error(tmp_path):
    with pytest.raises(NoRuleFilesError):
        load_rule_files(tmp_path)


def test_rule_file_with_broken_json_names_the_file(tmp_path):
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(RuleFileError, match="broken.json"):
        load_rule_files(tmp_path)


def test_failing_database_raises_database_error(dal):
    with dal._sf() as session:
        Base.metadata.drop_all(session.get_bind())     # now every query fails

    with pytest.raises(DatabaseError, match="not available"):
        dal.list_regions()
    with pytest.raises(DatabaseError):
        dal.save_result("bottle", "recyclable", 0.5, "DO")
