"""Starting the three subsystems and the settings of the web interface."""
import pytest

from classification import ClassificationEngine
from coach import CoachConfig
from web import ServiceStartupError, WebConfig, build_services, resolve_region
from web.config import load_env_file


def test_all_services_are_built(services):
    assert isinstance(services.classifier, ClassificationEngine)
    assert services.regions() == [("DO", "Dortmund")]
    assert services.rules.get_rule("recyclable", "DO").bin


def test_without_api_key_the_coach_uses_templates(services):
    assert services.coach.status()["language_model_available"] is False


def test_bad_database_url_gives_a_clear_startup_error():
    with pytest.raises(ServiceStartupError, match="could not start"):
        build_services(WebConfig(database_url="notadatabase://x"))


def test_env_file_gives_the_coach_its_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-the-file\n", encoding="utf-8")

    assert load_env_file(env_file) is True
    assert CoachConfig.from_env().api_key == "sk-from-the-file"


def test_env_file_does_not_replace_a_value_already_set(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-already-set")
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-the-file\n", encoding="utf-8")

    load_env_file(env_file)
    assert CoachConfig.from_env().api_key == "sk-already-set"


def test_missing_env_file_is_fine(tmp_path):
    assert load_env_file(tmp_path / "no_such_file") is False


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEFAULT_REGION", raising=False)
    config = WebConfig.from_env()
    assert config.database_url is None
    assert config.default_region == "DO"


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////data/waste.db")
    monkeypatch.setenv("DEFAULT_REGION", "Dortmund")
    config = WebConfig.from_env()
    assert config.database_url == "sqlite:////data/waste.db"
    assert config.default_region == "Dortmund"


@pytest.mark.parametrize("value", ["DO", "do", " Dortmund ", "dortmund"])
def test_region_code_or_name_is_accepted(value):
    assert resolve_region(value, [("DO", "Dortmund")]) == "DO"


def test_unknown_region_falls_back_to_the_first_known_one():
    assert resolve_region("Berlin", [("DO", "Dortmund"), ("MS", "Münster")]) == "DO"
