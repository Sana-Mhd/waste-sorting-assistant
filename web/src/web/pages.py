"""The pages of the app. Every page shows data; the work happens in the services and the workflow."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from classification import ClassificationConfig, InvalidImageError
from coach import charts

from .services import AppServices
from .workflow import ScanOutcome, ScanWorkflow

CATEGORY_LABELS = {
    "recyclable": "♻️ Recyclable",
    "compostable": "🌱 Compostable",
    "landfill": "🗑️ General waste",
}


class BasePage(ABC):
    """A page of the app. Subclasses only decide what to draw."""

    title: str = ""
    icon: str = ""

    def __init__(self, services: AppServices) -> None:
        self.services = services

    @property
    def label(self) -> str:
        """Text in the page menu, e.g. "📷 Scan an item"."""
        return f"{self.icon} {self.title}"

    @abstractmethod
    def render(self, region_code: str) -> None:
        """Draw the page for the selected region."""


class ScanPage(BasePage):
    """Upload a photo, get the bin and an explanation."""

    title = "Scan an item"
    icon = "📷"

    def __init__(self, services: AppServices) -> None:
        super().__init__(services)
        self.workflow = ScanWorkflow(services)

    def render(self, region_code: str) -> None:
        st.header(self.title)
        if self.services.classifier.is_demo_mode:
            st.info("Demo mode: no trained model was found, so every photo gets the same answer.")

        # Show the classifier's real limit; Streamlit would otherwise show its own 200 MB default.
        photo = st.file_uploader(
            "Photo of one waste item",
            type=["jpg", "jpeg", "png"],
            max_upload_size=math.ceil(ClassificationConfig.from_env().max_image_mb),
        )
        if photo is None:
            st.caption("Take a photo of a single item on a calm background and upload it.")
            return

        # Classify first: a broken file must give a friendly message, and st.image would crash on it.
        try:
            with st.spinner("Looking at your photo..."):
                outcome = self._scan_once(photo, region_code)
        except InvalidImageError as error:
            st.error(str(error))
            return

        left, right = st.columns([1, 2])
        left.image(photo, width="stretch")
        with right:
            self._show(outcome)

    def _scan_once(self, photo: UploadedFile, region_code: str) -> ScanOutcome:
        """Scan each upload only once.

        Streamlit runs this page again on every redraw while the photo is still in the
        uploader. Without this memory, each redraw would save the same photo as a new scan.
        Uploading a photo again counts as a new scan, because it gets a new file_id.
        """
        scans = st.session_state.setdefault("scans", {})
        if photo.file_id not in scans:
            scans[photo.file_id] = self.workflow.run(photo.getvalue(), region_code)
        return self.workflow.for_region(scans[photo.file_id], region_code)

    def _show(self, outcome: ScanOutcome) -> None:
        result = outcome.result
        if not outcome.is_confident:
            st.warning(
                f"Not sure about this one ({result.confidence:.0%}). "
                "Please take another photo with better light and only one item."
            )
            self._show_top3(outcome)
            return

        answer = outcome.explanation
        st.subheader(result.material.title())
        col1, col2 = st.columns(2)
        col1.metric("Category", CATEGORY_LABELS.get(result.category, result.category))
        col2.metric("Confidence", f"{result.confidence:.0%}")
        st.success(f"Put it in the **{answer.bin}**")
        st.write(answer.text)
        if answer.source == "template":
            st.caption("Offline answer, built from the local rule.")
        if not outcome.was_saved:
            st.caption("This scan could not be saved for the dashboard.")
        self._show_top3(outcome)

    @staticmethod
    def _show_top3(outcome: ScanOutcome) -> None:
        with st.expander("What else could it be?"):
            for material, probability in outcome.result.top3:
                st.progress(probability, text=f"{material}: {probability:.0%}")


class DashboardPage(BasePage):
    """Numbers and charts for the municipality."""

    title = "Municipality dashboard"
    icon = "📊"

    def render(self, region_code: str) -> None:
        st.header(self.title)
        analytics = self.services.analytics
        summary = analytics.summary(region_code)
        if summary.total_scans == 0:
            st.info("No scans in this region yet. Scan a few items first.")
            return

        col1, col2, col3 = st.columns(3)
        col1.metric("Total scans", summary.total_scans)
        col2.metric("Recycling rate", f"{summary.recycling_rate} %")
        col3.metric("Average confidence", f"{summary.average_confidence} %")

        left, right = st.columns(2)
        left.plotly_chart(charts.composition_chart(analytics, region_code), width="stretch")
        right.plotly_chart(charts.trend_chart(analytics, region_code, days=14), width="stretch")
        st.plotly_chart(charts.top_items_chart(analytics, region_code, limit=5), width="stretch")

        with st.expander("Show the numbers as a table"):
            st.dataframe(charts.composition_table(analytics, region_code), hide_index=True)


class AboutPage(BasePage):
    """What the app does and what it cannot do."""

    title = "About"
    icon = "ℹ️"

    def render(self, region_code: str) -> None:
        st.header(self.title)
        st.markdown(
            """
A resident photographs a waste item. The app recognises the material, tells you the
right bin for your region and explains why. Every scan feeds the municipality dashboard.

| Step | Subsystem |
|---|---|
| Photo → material and category | 1 · Classification Engine (MobileNetV2) |
| Category + region → bin | 2 · Data & Rules (SQLite) |
| Explanation and dashboard | 3 · AI Coach & Analytics |
| This page and Docker | 4 · Web Interface & Deployment |

**Known limits:** one item per photo works best. The model was trained mostly on photos
with a plain background, so cluttered photos can be less accurate. When the app is not
sure, it asks for a new photo instead of guessing.
"""
        )
        status = self.services.coach.status()
        st.caption(
            f"Model: {'demo mode' if self.services.classifier.is_demo_mode else 'MobileNetV2'} · "
            f"Coach: {'OpenAI' if status['language_model_available'] else 'offline templates'} · "
            f"Cached explanations: {status['cached_explanations']}"
        )
