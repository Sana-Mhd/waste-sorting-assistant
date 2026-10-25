"""Subsystem 3: AI Coach & Analytics.

Two things the application needs once a photo has been classified: a short
explanation of why the item belongs in that bin, and the numbers behind the
municipality dashboard.

Public API for the other subsystems:

    from data_rules import create_services
    from coach import create_coach_services, charts

    dal, rule_engine = create_services()
    coach, analytics = create_coach_services(dal, rule_engine)

    answer = coach.explain("plastic bottle", "recyclable", "DO")
    answer.text, answer.bin, answer.source

    analytics.summary("DO")
    charts.composition_chart(analytics, "DO")
"""
from . import charts
from .analytics import RECYCLED_CATEGORIES, AnalyticsService
from .cache import BaseCache, MemoryCache, SQLiteCache, make_key
from .client import OpenAIClient
from .coach import CoachService
from .config import LANGUAGES, MAX_WORDS, CoachConfig
from .exceptions import CacheUnavailable, CoachError, LanguageModelUnavailable
from .explainers import (
    BaseExplainer,
    LanguageModelExplainer,
    TemplateExplainer,
    shorten,
)
from .schemas import Explanation, Summary
from .services import create_coach_services

__version__ = "1.0.0"

#: Everything the other subsystems are allowed to rely on.
__all__ = [
    "LANGUAGES",
    "MAX_WORDS",
    "RECYCLED_CATEGORIES",
    "AnalyticsService",
    "BaseCache",
    "BaseExplainer",
    "CacheUnavailable",
    "CoachConfig",
    "CoachError",
    "CoachService",
    "Explanation",
    "LanguageModelExplainer",
    "LanguageModelUnavailable",
    "MemoryCache",
    "OpenAIClient",
    "SQLiteCache",
    "Summary",
    "TemplateExplainer",
    "__version__",
    "charts",
    "create_coach_services",
    "make_key",
    "shorten",
]
