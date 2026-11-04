"""The real app.py, run headless with Streamlit's AppTest."""
from data_rules import create_services
from streamlit.testing.v1 import AppTest

from conftest import APP_FILE, png_bytes

TIMEOUT = 60  # the first run imports torch and loads the model


def run_app() -> AppTest:
    app = AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT)
    return app.run()


def test_app_starts_on_the_scan_page(app_env):
    app = run_app()
    assert not app.exception
    assert "Waste Sorting" in app.title[0].value
    assert app.header[0].value == "Scan an item"


def test_sidebar_offers_dortmund_and_three_pages(app_env):
    app = run_app()
    assert app.sidebar.selectbox[0].value == "DO"
    assert len(app.sidebar.radio[0].options) == 3


def test_dashboard_without_scans_shows_a_hint(app_env):
    app = run_app()
    app.sidebar.radio[0].set_value("📊 Municipality dashboard").run()
    assert not app.exception
    assert "No scans" in app.info[0].value


def test_upload_box_uses_the_default_limit_of_the_classifier(app_env, monkeypatch):
    monkeypatch.delenv("MAX_IMAGE_MB", raising=False)
    app = run_app()
    assert app.file_uploader[0].proto.max_upload_size_mb == 10


def test_upload_box_follows_the_max_image_mb_setting(app_env, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_MB", "5")
    app = run_app()
    assert app.file_uploader[0].proto.max_upload_size_mb == 5


def count_saved_scans(app_env) -> int:
    dal, _ = create_services(f"sqlite:///{app_env / 'app.db'}")
    return len(dal.get_results(region_code="DO"))


def test_redrawing_the_page_does_not_save_the_photo_again(app_env, monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0")     # always take the path that saves
    app = run_app()

    app.file_uploader[0].set_value(("photo.png", png_bytes(), "image/png")).run()
    assert not app.exception
    assert app.success                                  # the answer is on the page
    assert count_saved_scans(app_env) == 1

    app.run()                                           # the redraw that used to save it twice
    assert not app.exception
    assert app.success                                  # the answer is still shown
    assert count_saved_scans(app_env) == 1


def test_uploading_again_counts_as_a_new_scan(app_env, monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0")
    app = run_app()

    app.file_uploader[0].set_value(("photo.png", png_bytes(), "image/png")).run()
    app.file_uploader[0].set_value(("photo.png", png_bytes(), "image/png")).run()

    assert not app.exception
    assert count_saved_scans(app_env) == 2


def test_about_page_renders(app_env):
    app = run_app()
    app.sidebar.radio[0].set_value("ℹ️ About").run()
    assert not app.exception
    assert app.header[0].value == "About"
