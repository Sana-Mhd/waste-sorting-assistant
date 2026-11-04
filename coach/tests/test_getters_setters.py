"""Getters and setters of the coach classes (Hometask 1)."""
from coach.analytics import AnalyticsService
from coach.cache import MemoryCache
from coach.client import OpenAIClient
from coach.coach import CoachService
from coach.config import CoachConfig
from coach.explainers import TemplateExplainer


def make_coach() -> CoachService:
    config = CoachConfig(api_key="")
    explainer = TemplateExplainer(config.language, config.max_words)
    return CoachService(object(), MemoryCache(), explainer, explainer, config)


def test_coach_getters_and_setters():
    coach = make_coach()
    config, rules, cache = CoachConfig(api_key=""), object(), MemoryCache()
    explainer, fallback = TemplateExplainer("en", 40), TemplateExplainer("de", 40)

    coach.config = config
    coach.rules = rules
    coach.cache = cache
    coach.explainer = explainer
    coach.fallback = fallback

    assert coach.config is config
    assert coach.rules is rules
    assert coach.cache is cache
    assert coach.explainer is explainer
    assert coach.fallback is fallback


def test_analytics_getter_and_setter():
    first, second = object(), object()
    analytics = AnalyticsService(first)
    assert analytics.dal is first

    analytics.dal = second
    assert analytics.dal is second


def test_client_getter_and_setter():
    client = OpenAIClient(CoachConfig(api_key=""))
    assert client.is_available() is False

    with_key = CoachConfig(api_key="sk-test")
    client.config = with_key

    assert client.config is with_key
    assert client.is_available() is True
