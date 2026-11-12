"""Subsystem 4: the Flask app that connects subsystems 1-3.

Run from the repository root:

    python web/src/web/app.py
"""
import logging
import math
import signal
import sys
from functools import lru_cache
from pathlib import Path

# Make the four packages importable when this file is run directly.
# (In Docker PYTHONPATH already contains them; adding them twice does no harm.)
ROOT = Path(__file__).resolve().parents[3]
for package_dir in ("classification", "data_rules", "coach", "web"):
    path = str(ROOT / package_dir / "src")
    if path not in sys.path:
        sys.path.insert(0, path)

from flask import Flask, Response, redirect, render_template, request, url_for  # noqa: E402
from plotly.offline import get_plotlyjs  # noqa: E402
from waitress import serve  # noqa: E402
from werkzeug.exceptions import RequestEntityTooLarge  # noqa: E402

from classification import ClassificationConfig, InvalidImageError  # noqa: E402
from web.api import create_api  # noqa: E402
from web.config import WebConfig, load_env_file, resolve_region  # noqa: E402
from web.exceptions import ServiceStartupError  # noqa: E402
from web.pages import AboutPage, BasePage, DashboardPage, ScanPage  # noqa: E402
from web.services import AppServices, build_services  # noqa: E402


@lru_cache(maxsize=1)
def plotly_script() -> str:
    """Plotly's script comes from the installed package, so the charts work without internet."""
    return get_plotlyjs()


def create_app(services: AppServices | None = None) -> Flask:
    """Build the Flask app. The services start once here, not on every click.

    Args:
        services: ready services, e.g. with a DummyClassifier in tests;
            by default they are built from the environment.

    Returns:
        The app. If the services cannot start, it shows the reason on every page.
    """
    config = WebConfig.from_env()
    app = Flask("web")
    # One extra MB: the upload also contains the form around the photo.
    max_image_mb = ClassificationConfig.from_env().max_image_mb
    app.config["MAX_CONTENT_LENGTH"] = (math.ceil(max_image_mb) + 1) * 1024 * 1024
    app.add_template_filter(lambda share: f"{share:.0%}", "percent")

    try:
        services = services or build_services(config)
    except ServiceStartupError as error:
        _show_startup_error(app, config, str(error))
        return app

    _add_routes(app, services, config, max_image_mb)
    return app


def _show_startup_error(app: Flask, config: WebConfig, message: str) -> None:
    """Answer every request with the startup problem instead of a broken page."""

    @app.before_request
    def startup_error() -> tuple[str, int] | None:
        """Show the error page for every page; let CSS and other static files through."""
        if request.endpoint == "static":
            return None
        return render_template("startup_error.html", app_title=config.title, message=message), 503


def _add_routes(app: Flask, services: AppServices, config: WebConfig, max_image_mb: float) -> None:
    """Connect the addresses of the app to its pages."""
    scan_page = ScanPage(services)
    dashboard_page = DashboardPage(services)
    about_page = AboutPage(services)
    pages: list[BasePage] = [scan_page, dashboard_page, about_page]
    app.register_blueprint(create_api(services, config))

    def selected_region() -> str:
        """The region in the address, or the default one. Unknown values fall back to a known region."""
        wanted = request.args.get("region") or config.default_region
        return resolve_region(wanted, services.regions())

    @app.context_processor
    def shared_page_data() -> dict:
        """What the layout around every page needs."""
        regions = services.regions() or [(config.default_region, config.default_region)]
        return {"app_title": config.title, "pages": pages, "regions": regions}

    @app.get("/", endpoint=scan_page.endpoint)
    def show_scan_page() -> str:
        """The start page: upload form and, after a scan, its result."""
        return scan_page.render(selected_region())

    @app.post("/scan")
    def upload_photo() -> Response | tuple[str, int]:
        """Classify the uploaded photo, then send the browser to its result."""
        region_code = selected_region()
        try:
            scan_id = scan_page.handle_upload(request.files.get("photo"), region_code)
        except InvalidImageError as error:
            return scan_page.render(region_code, error=str(error)), 400
        # Send the browser to a normal page, so that reloading it cannot save the photo again.
        return redirect(url_for(scan_page.endpoint, scan=scan_id, region=region_code), code=303)

    @app.get("/dashboard", endpoint=dashboard_page.endpoint)
    def show_dashboard_page() -> str:
        """The municipality dashboard with statistics and charts."""
        return dashboard_page.render(selected_region())

    @app.get("/about", endpoint=about_page.endpoint)
    def show_about_page() -> str:
        """A short page about the project and its status."""
        return about_page.render(selected_region())

    @app.get("/plotly.min.js")
    def plotly_js() -> Response:
        """The chart library, served locally so the dashboard works without internet."""
        return Response(plotly_script(), mimetype="text/javascript")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Used by Docker to check that the app is running."""
        return {"status": "ok"}

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error: RequestEntityTooLarge) -> tuple[str, int]:
        """Show a friendly message instead of an error page when the photo is too big."""
        message = f"The image is too large. The maximum size is {max_image_mb:g} MB."
        return scan_page.render(selected_region(), error=message), 413


def main() -> None:
    """Start the app with Waitress, a server that also works on Windows."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_env_file(ROOT / ".env")
    # Docker stops the app with SIGTERM; without this it would wait 10 s and then kill it.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    config = WebConfig.from_env()
    logging.getLogger(__name__).info("Open http://localhost:%s", config.port)
    serve(create_app(), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
