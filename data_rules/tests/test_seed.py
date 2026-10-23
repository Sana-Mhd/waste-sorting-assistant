import json

import pytest

from data_rules.seed import load_rule_files, seed_database


def test_dortmund_is_the_only_seeded_region(dal):
    assert dal.list_regions() == [("DO", "Dortmund")]


def test_dortmund_has_one_rule_per_category(dal):
    rules = dal.get_rules("DO")
    assert [r.category for r in rules] == ["compostable", "landfill", "recyclable"]
    assert all(r.bin and r.reason for r in rules)


def test_seed_can_run_twice_without_duplicates(dal):
    seed_database(dal)
    seed_database(dal)
    assert len(dal.get_rules("DO")) == 3
    assert len(dal.list_regions()) == 1


def _write(tmp_path, name, data):
    (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")


def test_new_region_by_adding_a_file_only(dal, tmp_path):
    _write(tmp_path, "koeln.json", {
        "region": {"code": "KO", "name": "Koeln"},
        "rules": [{"category": "landfill", "bin": "Black bin", "reason": "Residual waste."}],
    })
    seed_database(dal, tmp_path)
    assert dal.get_rule("landfill", "KO").bin == "Black bin"


def test_rule_file_with_unknown_category_is_rejected(tmp_path):
    _write(tmp_path, "bad.json", {
        "region": {"code": "XX", "name": "Nowhere"},
        "rules": [{"category": "metal", "bin": "b", "reason": "r"}],
    })
    with pytest.raises(ValueError, match="bad.json"):
        load_rule_files(tmp_path)


def test_rule_file_with_missing_field_is_rejected(tmp_path):
    _write(tmp_path, "bad.json", {"region": {"code": "XX"}, "rules": []})
    with pytest.raises(ValueError, match="bad.json"):
        load_rule_files(tmp_path)


def test_empty_rules_folder_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_rule_files(tmp_path)
