"""Subsystem 4: Web Interface & Deployment.

The Streamlit app (app.py) that connects the classification engine, the rules
and the AI coach. The parts other code may rely on:

    from web import WebConfig, build_services, ScanWorkflow

    services = build_services(WebConfig.from_env())
    outcome = ScanWorkflow(services).run(photo_bytes, "DO")
    outcome.result, outcome.explanation, outcome.saved_id
"""
from .config import WebConfig, resolve_region
from .exceptions import ServiceStartupError, WebError
from .services import AppServices, build_services
from .workflow import ScanOutcome, ScanWorkflow

__all__ = [
    "AppServices",
    "ScanOutcome",
    "ScanWorkflow",
    "ServiceStartupError",
    "WebConfig",
    "WebError",
    "build_services",
    "resolve_region",
]
