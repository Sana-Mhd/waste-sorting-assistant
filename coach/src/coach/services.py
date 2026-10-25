"""One call that builds everything subsystem 3 offers.

The web interface should not have to know which objects this subsystem is made
of. It asks for the two services and uses them:

    from data_rules import create_services
    from coach import create_coach_services

    dal, rule_engine = create_services()
    coach, analytics = create_coach_services(dal, rule_engine)
"""
from __future__ import annotations

import logging

from .analytics import AnalyticsService
from .coach import CoachService
from .config import CoachConfig

logger = logging.getLogger(__name__)


def create_coach_services(
    data_access,
    rule_engine,
    config: CoachConfig | None = None,
) -> tuple[CoachService, AnalyticsService]:
    """Build the coach and the analytics from the two services of subsystem 2.

    Args:
        data_access: a data_rules.DataAccessLayer, read by the analytics.
        rule_engine: a data_rules.RuleEngine, asked by the coach.
        config: settings; read from the environment when not given.

    Returns:
        (coach, analytics)
    """
    config = config or CoachConfig.from_env()
    coach = CoachService(rule_engine, config=config)

    if not coach.explainer.is_available():
        logger.info(
            "No OPENAI_API_KEY found: explanations are built from the local rule."
        )

    return coach, AnalyticsService(data_access)
