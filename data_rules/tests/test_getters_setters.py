"""Getters and setters of the data_rules classes (Hometask 1)."""
from pathlib import Path

from data_rules import RuleFileLoader
from data_rules.data_access import DataAccessLayer
from data_rules.seed import DEFAULT_RULES_DIR


def test_data_access_layer_session_factory(dal):
    factory = dal.session_factory
    dal.session_factory = factory
    assert dal.session_factory is factory
    assert dal.list_regions() == [("DO", "Dortmund")]


def test_rule_engine_dal(engine_rules, dal):
    other = DataAccessLayer(dal.session_factory)
    engine_rules.dal = other
    assert engine_rules.dal is other
    assert engine_rules.get_rule("recyclable", "DO").bin


def test_loader_uses_the_default_folder(monkeypatch):
    monkeypatch.delenv("RULES_DIR", raising=False)
    assert RuleFileLoader().directory == DEFAULT_RULES_DIR


def test_loader_directory_setter_gives_a_path(tmp_path):
    loader = RuleFileLoader()
    loader.directory = str(tmp_path)
    assert loader.directory == Path(tmp_path)


def test_loader_loads_dortmund():
    regions = [data["region"]["code"] for data in RuleFileLoader(DEFAULT_RULES_DIR).load()]
    assert "DO" in regions
