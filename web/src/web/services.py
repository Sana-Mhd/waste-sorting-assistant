"""Builds the services of subsystems 1-3 once and holds them together.

This is the only place where the three subsystems are created. The pages and
the scan workflow receive an AppServices object and never build anything themselves.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from classification import ClassificationEngine
from coach import AnalyticsService, CoachConfig, CoachService, create_coach_services
from data_rules import DataAccessLayer, RuleEngine, create_services

from .config import WebConfig
from .exceptions import ServiceStartupError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppServices:
    """The services of the other three subsystems, built once per app start."""

    classifier: ClassificationEngine   # subsystem 1
    dal: DataAccessLayer               # subsystem 2: stored scans, regions
    rules: RuleEngine                  # subsystem 2: which bin
    coach: CoachService                # subsystem 3: explanation
    analytics: AnalyticsService        # subsystem 3: dashboard numbers

    def regions(self) -> list[tuple[str, str]]:
        """Known regions as (code, name), e.g. [("DO", "Dortmund")]."""
        return self.dal.list_regions()


def build_services(
    config: WebConfig,
    classifier: ClassificationEngine | None = None,
    coach_config: CoachConfig | None = None,
) -> AppServices:
    """Start the three subsystems.

    Args:
        config: settings of the web interface (database location).
        classifier: a ready engine, e.g. with a DummyClassifier in tests;
            by default the trained model (or demo mode if it is missing).
        coach_config: settings of the coach; read from the environment by default.

    Raises:
        ServiceStartupError: if the database or one of the services cannot be started.
    """
    try:
        dal, rules = create_services(config.database_url)
        coach, analytics = create_coach_services(dal, rules, coach_config)
        classifier = classifier or ClassificationEngine.from_config()
    except Exception as error:
        logger.exception("Could not start the services")
        raise ServiceStartupError(
            "The app could not start because the database or a service is not available. "
            "Please check DATABASE_URL and the logs."
        ) from error

    logger.info("Services ready (demo mode: %s, coach: %s)",
                classifier.is_demo_mode, type(coach.explainer).__name__)
    return AppServices(classifier, dal, rules, coach, analytics)
