"""Subsystem 4 - Web Interface.

OWNER: <name>

Run it from the project root with:

    streamlit run src/web/app.py

This file is the only place where the four subsystems meet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make `src` importable when Streamlit runs this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.classification import classify              # noqa: E402
from src.coach import AnalyticsService, CoachService  # noqa: E402
from src.data import Repository, ScanRecord          # noqa: E402

st.set_page_config(page_title="Waste Sorting Assistant", page_icon="♻️", layout="wide")


@st.cache_resource
def get_services():
    """Build the three services once and reuse them."""
    repository = Repository()
    return repository, CoachService(repository), AnalyticsService(repository)


repository, coach, analytics = get_services()


def scan_page() -> None:
    st.header("Scan a waste item")

    region = st.selectbox("Your region", repository.regions())
    photo = st.file_uploader("Photo of the item", type=["jpg", "jpeg", "png"])

    if photo is None:
        st.info("Upload a photo to get a recommendation.")
        return

    left, right = st.columns([1, 2])
    with left:
        st.image(photo, use_container_width=True)

    with right:
        result = classify(photo.name)

        if not result.is_confident:
            st.warning(
                f"Not sure about this one ({result.confidence:.0%} confidence). "
                "Please take another photo with better light."
            )
            return

        rule = repository.get_rule(result.category, region)

        st.subheader(result.item.title())
        st.metric("Category", result.category, f"{result.confidence:.0%} confident")
        st.success(f"Put it in the **{rule.bin_name}** ({rule.bin_color} bin)")

        with st.spinner("Asking the coach..."):
            st.write(coach.explain(result.item, region))

        repository.save_scan(
            ScanRecord(
                item=result.item,
                category=result.category,
                region=region,
                confidence=result.confidence,
            )
        )


def dashboard_page() -> None:
    st.header("Municipality dashboard")

    region = st.selectbox("Region", repository.regions(), key="dashboard_region")
    total = analytics.total_scans(region)

    if total == 0:
        st.info("No scans yet. Scan a few items first.")
        return

    col1, col2 = st.columns(2)
    col1.metric("Total scans", total)
    col2.metric("Recycling rate", f"{analytics.recycling_rate(region)} %")

    st.subheader("Waste composition")
    st.bar_chart(analytics.composition(region))

    st.subheader("Scans over time")
    st.line_chart(analytics.trend(region), x="date", y="scans")


st.title("♻️ Waste Sorting & Recycling Assistant")
page = st.sidebar.radio("Page", ["Scan an item", "Municipality dashboard"])

if page == "Scan an item":
    scan_page()
else:
    dashboard_page()
