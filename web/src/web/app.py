"""Subsystem 4: the Streamlit app that connects subsystems 1-3.

Run from the repository root:

    streamlit run web/src/web/app.py
"""
import logging
import sys
from pathlib import Path

# Make the four packages importable when Streamlit runs this file directly.
# (In Docker PYTHONPATH already contains them; adding them twice does no harm.)
ROOT = Path(__file__).resolve().parents[3]
for package_dir in ("classification", "data_rules", "coach", "web"):
    path = str(ROOT / package_dir / "src")
    if path not in sys.path:
        sys.path.insert(0, path)

import streamlit as st  # noqa: E402

from web.config import WebConfig, load_env_file, resolve_region  # noqa: E402
from web.exceptions import ServiceStartupError  # noqa: E402
from web.pages import AboutPage, BasePage, DashboardPage, ScanPage  # noqa: E402
from web.services import AppServices, build_services  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
load_env_file(ROOT / ".env")


@st.cache_resource(show_spinner="Starting the assistant...")
def load_services() -> AppServices:
    """Build the services once per server, not on every click."""
    return build_services(WebConfig.from_env())


def main() -> None:
    config = WebConfig.from_env()
    st.set_page_config(page_title=config.title, page_icon="♻️", layout="wide")
    st.title(f"♻️ {config.title}")

    try:
        services = load_services()
    except ServiceStartupError as error:
        st.error(str(error))
        st.stop()

    pages: list[BasePage] = [ScanPage(services), DashboardPage(services), AboutPage(services)]

    with st.sidebar:
        regions = services.regions()
        codes = [code for code, _ in regions] or [config.default_region]
        names = dict(regions)
        default = resolve_region(config.default_region, regions)
        region_code = st.selectbox(
            "Your region", codes, index=codes.index(default) if default in codes else 0,
            format_func=lambda code: f"{names.get(code, code)} ({code})",
        )
        by_label = {page.label: page for page in pages}
        chosen = st.radio("Page", list(by_label))

    by_label[chosen].render(region_code)


main()
