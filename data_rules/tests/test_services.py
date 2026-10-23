from data_rules import create_services
from data_rules.config import DEFAULT_DATABASE_URL, database_url


def test_database_path_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == DEFAULT_DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/other.db")
    assert database_url() == "sqlite:////tmp/other.db"


def test_data_survives_a_restart(tmp_path):
    url = f"sqlite:///{tmp_path}/waste.db"
    dal, engine = create_services(url)
    dal.save_result("glass bottle", "recyclable", 0.95, "DO")
    dal2, engine2 = create_services(url)              # "restart": new objects, same file
    assert len(dal2.get_results()) == 1
    assert len(dal2.get_rules("DO")) == 3              # seed did not duplicate anything
    assert "Brown" in engine2.get_rule("compostable", "DO").bin
