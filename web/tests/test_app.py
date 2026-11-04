"""The real Flask app, called through Flask's test client."""
import io
from urllib.parse import parse_qs, urlparse

from data_rules import create_services
from flask.testing import FlaskClient
from web.app import create_app

from conftest import make_services, png_bytes


def real_client() -> FlaskClient:
    """The whole app as it really starts, with the settings of the environment."""
    return create_app().test_client()


def client_with(services) -> FlaskClient:
    return create_app(services).test_client()


def upload(client: FlaskClient, data: bytes | None = None, filename: str = "photo.png"):
    """Post a photo to the scan form, without following the redirect."""
    photo = png_bytes() if data is None else data
    return client.post("/scan?region=DO", data={"photo": (io.BytesIO(photo), filename)},
                       content_type="multipart/form-data")


def count_saved_scans(app_env) -> int:
    dal, _ = create_services(f"sqlite:///{app_env / 'app.db'}")
    return len(dal.get_results(region_code="DO"))


def test_app_starts_on_the_scan_page(app_env):
    response = real_client().get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Waste Sorting" in html
    assert "<h2>Scan an item</h2>" in html


def test_sidebar_offers_dortmund_and_three_pages(app_env):
    html = real_client().get("/").get_data(as_text=True)
    assert '<option value="DO" selected>Dortmund (DO)</option>' in html
    assert "Scan an item</a>" in html
    assert "Municipality dashboard</a>" in html
    assert "About</a>" in html


def test_dashboard_without_scans_shows_a_hint(app_env):
    html = real_client().get("/dashboard").get_data(as_text=True)
    assert "No scans" in html
    assert "plotly.min.js" not in html


def test_about_page_renders(app_env):
    response = real_client().get("/about")
    assert response.status_code == 200
    assert "<h2>About</h2>" in response.get_data(as_text=True)
    assert "offline templates" in response.get_data(as_text=True)


def test_unknown_region_falls_back_to_a_known_one(app_env):
    html = real_client().get("/?region=XX").get_data(as_text=True)
    assert '<option value="DO" selected>' in html


def test_health_check_answers(app_env):
    response = real_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_upload_form_shows_the_default_limit_of_the_classifier(app_env, monkeypatch):
    monkeypatch.delenv("MAX_IMAGE_MB", raising=False)
    assert "up to 10 MB" in real_client().get("/").get_data(as_text=True)


def test_upload_form_follows_the_max_image_mb_setting(app_env, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_MB", "5")
    assert "up to 5 MB" in real_client().get("/").get_data(as_text=True)


def test_confident_scan_shows_the_answer_and_the_photo(tmp_path):
    client = client_with(make_services(tmp_path, "plastic", 0.9))
    response = upload(client)
    assert response.status_code == 303

    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Plastic" in html
    assert "Put it in the" in html
    assert "90%" in html
    assert 'src="data:image/png;base64,' in html


def test_uncertain_scan_asks_for_a_new_photo_and_is_not_saved(tmp_path):
    services = make_services(tmp_path, "glass", 0.3)
    client = client_with(services)

    html = client.get(upload(client).headers["Location"]).get_data(as_text=True)

    assert "Not sure about this one (30%)" in html
    assert "Put it in the" not in html
    assert "What else could it be?" in html
    assert services.analytics.total_scans("DO") == 0


def test_reloading_the_result_page_does_not_save_the_photo_again(app_env, monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0")     # always take the path that saves
    client = real_client()

    result_page = upload(client).headers["Location"]
    assert "Put it in the" in client.get(result_page).get_data(as_text=True)
    assert count_saved_scans(app_env) == 1

    assert "Put it in the" in client.get(result_page).get_data(as_text=True)   # the reload
    assert count_saved_scans(app_env) == 1


def test_uploading_again_counts_as_a_new_scan(app_env, monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0")
    client = real_client()

    first = upload(client).headers["Location"]
    second = upload(client).headers["Location"]

    assert first != second
    assert count_saved_scans(app_env) == 2


def test_result_page_keeps_the_scan_when_the_region_form_is_used(tmp_path):
    client = client_with(make_services(tmp_path))
    result_page = upload(client).headers["Location"]
    scan_id = parse_qs(urlparse(result_page).query)["scan"][0]

    html = client.get(result_page).get_data(as_text=True)

    assert f'<input type="hidden" name="scan" value="{scan_id}">' in html


def test_unknown_scan_id_shows_the_empty_form(tmp_path):
    html = client_with(make_services(tmp_path)).get("/?scan=nothing").get_data(as_text=True)
    assert "Take a photo of a single item" in html
    assert "Put it in the" not in html


def test_broken_file_gets_a_friendly_message(tmp_path):
    services = make_services(tmp_path)
    response = upload(client_with(services), b"definitely not a photo")

    assert response.status_code == 400
    assert "not a readable image" in response.get_data(as_text=True)
    assert services.analytics.total_scans("DO") == 0


def test_no_file_chosen_gets_a_friendly_message(tmp_path):
    response = client_with(make_services(tmp_path)).post("/scan?region=DO")
    assert response.status_code == 400
    assert "Please choose a photo" in response.get_data(as_text=True)


def test_file_over_the_limit_is_refused_by_the_classifier(app_env, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_MB", "1")
    response = upload(real_client(), b"x" * int(1.5 * 1024 * 1024))
    assert response.status_code == 400
    assert "maximum size is 1 MB" in response.get_data(as_text=True)


def test_file_far_over_the_limit_is_refused_by_flask(app_env, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_MB", "1")
    response = upload(real_client(), b"x" * (3 * 1024 * 1024))
    assert response.status_code == 413
    assert "maximum size is 1 MB" in response.get_data(as_text=True)


def test_text_from_the_explanation_cannot_add_html_to_the_page(tmp_path, monkeypatch):
    services = make_services(tmp_path)
    explain = services.coach.explain_result

    def with_script(result, region_code):
        answer = explain(result, region_code)
        return type(answer)(**{**vars(answer), "text": "<script>alert(1)</script>"})

    monkeypatch.setattr(services.coach, "explain_result", with_script)
    client = client_with(services)

    html = client.get(upload(client).headers["Location"]).get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_dashboard_shows_numbers_three_charts_and_the_table(tmp_path):
    client = client_with(make_services(tmp_path))
    upload(client)

    html = client.get("/dashboard?region=DO").get_data(as_text=True)

    assert "Total scans" in html
    assert html.count("plotly-graph-div") == 3
    assert "Share of scans" in html
    assert "plotly.min.js" in html


def test_plotly_script_is_served_by_the_app_itself(tmp_path):
    response = client_with(make_services(tmp_path)).get("/plotly.min.js")
    assert response.status_code == 200
    assert response.mimetype == "text/javascript"
    assert b"plotly" in response.data[:2000].lower()


def test_failed_start_shows_the_reason_on_every_page(app_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "notadatabase://x")
    client = real_client()

    for address in ("/", "/dashboard", "/about", "/health"):
        response = client.get(address)
        assert response.status_code == 503
        assert "could not start" in response.get_data(as_text=True)
