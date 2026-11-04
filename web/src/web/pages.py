"""The pages of the app. Every page shows data; the work happens in the services and the workflow."""
from __future__ import annotations

import base64
import math
from abc import ABC, abstractmethod

from flask import render_template, request
from markupsafe import Markup
from plotly.graph_objects import Figure
from werkzeug.datastructures import FileStorage

from classification import ClassificationConfig, InvalidImageError
from coach import charts

from .scan_store import ScanStore
from .services import AppServices
from .workflow import ScanWorkflow

CATEGORY_LABELS = {
    "recyclable": "♻️ Recyclable",
    "compostable": "🌱 Compostable",
    "landfill": "🗑️ General waste",
}


class BasePage(ABC):
    """A page of the app. Subclasses only decide what to show."""

    title: str = ""
    icon: str = ""
    endpoint: str = ""      # the name of the page's Flask route, used for the links

    def __init__(self, services: AppServices) -> None:
        self.services = services

    @property
    def label(self) -> str:
        """Text in the page menu, e.g. "📷 Scan an item"."""
        return f"{self.icon} {self.title}"

    @abstractmethod
    def render(self, region_code: str) -> str:
        """Return the HTML of the page for the selected region."""


class ScanPage(BasePage):
    """Upload a photo, get the bin and an explanation."""

    title = "Scan an item"
    icon = "📷"
    endpoint = "scan_page"

    def __init__(self, services: AppServices, store: ScanStore | None = None) -> None:
        super().__init__(services)
        self.workflow = ScanWorkflow(services)
        self.store = store or ScanStore()

    def handle_upload(self, photo: FileStorage | None, region_code: str) -> str:
        """Scan an uploaded photo once and return the id of its result page.

        Raises:
            InvalidImageError: if no file was chosen or it is not a usable photo.
        """
        if photo is None or not photo.filename:
            raise InvalidImageError("Please choose a photo first.")
        image = photo.read()
        return self.store.add(self.workflow.run(image, region_code), image)

    def render(self, region_code: str, error: str | None = None) -> str:
        """Show the upload form, and the scan named in the address if there is one.

        Args:
            region_code: the selected region.
            error: a message for the user about a failed upload.
        """
        stored = None if error else self.store.get(request.args.get("scan"))
        return render_template(
            "scan.html",
            page=self,
            region_code=region_code,
            error=error,
            scan_id=request.args.get("scan") if stored else None,
            outcome=self.workflow.for_region(stored.outcome, region_code) if stored else None,
            photo_src=self._photo_src(stored.photo) if stored else None,
            max_image_mb=math.ceil(ClassificationConfig.from_env().max_image_mb),
            demo_mode=self.services.classifier.is_demo_mode,
            category_labels=CATEGORY_LABELS,
        )

    @staticmethod
    def _photo_src(photo: bytes) -> str:
        """Put the photo into the page itself. The classifier already checked it is a JPEG or PNG."""
        media_type = "image/png" if photo.startswith(b"\x89PNG") else "image/jpeg"
        return f"data:{media_type};base64,{base64.b64encode(photo).decode('ascii')}"


class DashboardPage(BasePage):
    """Numbers and charts for the municipality."""

    title = "Municipality dashboard"
    icon = "📊"
    endpoint = "dashboard_page"

    def render(self, region_code: str) -> str:
        analytics = self.services.analytics
        summary = analytics.summary(region_code)
        if summary.total_scans == 0:
            return render_template("dashboard.html", page=self, region_code=region_code, summary=summary)

        return render_template(
            "dashboard.html",
            page=self,
            region_code=region_code,
            summary=summary,
            composition=self._chart_html(charts.composition_chart(analytics, region_code)),
            trend=self._chart_html(charts.trend_chart(analytics, region_code, days=14)),
            top_items=self._chart_html(charts.top_items_chart(analytics, region_code, limit=5)),
            table=charts.composition_table(analytics, region_code),
        )

    @staticmethod
    def _chart_html(figure: Figure) -> Markup:
        """Turn a Plotly chart into HTML. The Plotly script itself is loaded once by the page."""
        return Markup(figure.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True}))


class AboutPage(BasePage):
    """What the app does and what it cannot do."""

    title = "About"
    icon = "ℹ️"
    endpoint = "about_page"

    def render(self, region_code: str) -> str:
        return render_template(
            "about.html",
            page=self,
            region_code=region_code,
            demo_mode=self.services.classifier.is_demo_mode,
            coach_status=self.services.coach.status(),
        )
