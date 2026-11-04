import io
import sys
from pathlib import Path

import pytest
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
for package_dir in ("classification", "data_rules", "coach", "web"):
    sys.path.insert(0, str(ROOT / package_dir / "src"))

from classification import ClassificationEngine, DummyClassifier, ImagePreprocessor  # noqa: E402
from coach import CoachConfig  # noqa: E402
from web import WebConfig, build_services  # noqa: E402

APP_FILE = ROOT / "web" / "src" / "web" / "app.py"


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), "green").save(buffer, "PNG")
    return buffer.getvalue()


def make_services(tmp_path, material="plastic", confidence=0.9):
    """Real subsystems 2 and 3 on a temporary database, a dummy classifier, no OpenAI key."""
    return build_services(
        WebConfig(database_url=f"sqlite:///{tmp_path / 'test.db'}"),
        classifier=ClassificationEngine(DummyClassifier(material, confidence), ImagePreprocessor()),
        coach_config=CoachConfig(api_key="", cache_path=str(tmp_path / "cache.db")),
    )


@pytest.fixture
def services(tmp_path):
    return make_services(tmp_path)


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """Environment for running the real app.py: temporary files, no API key."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("COACH_CACHE_PATH", str(tmp_path / "coach_cache.db"))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    st.cache_resource.clear()      # every test gets fresh services on its own database
    yield tmp_path
    st.cache_resource.clear()
