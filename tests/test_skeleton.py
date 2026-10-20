"""A few tests that prove the skeleton holds together.

Each subsystem adds its own test file next to this one.
"""

from src.classification import CATEGORIES, classify
from src.coach import AnalyticsService, CoachService, ExplanationCache
from src.data import Repository, ScanRecord


def test_classify_returns_a_known_category():
    result = classify("any.jpg")
    assert result.category in CATEGORIES
    assert 0.0 <= result.confidence <= 1.0


def test_repository_knows_the_dortmund_rules():
    repository = Repository()
    rule = repository.get_rule("recyclable", "Dortmund")
    assert rule.bin_name


def test_cache_stores_and_returns_a_text():
    cache = ExplanationCache()
    key = cache.make_key("plastic bottle", "Dortmund")
    assert cache.get(key) is None
    cache.set(key, "hello")
    assert cache.get(key) == "hello"


def test_coach_falls_back_when_the_api_is_not_available():
    repository = Repository()
    coach = CoachService(repository)
    coach.client.api_key = ""          # pretend there is no key
    text = coach.explain("plastic bottle", "Dortmund")
    assert "Dortmund" in text


def test_analytics_counts_the_scans():
    repository = Repository()
    for category in ("recyclable", "recyclable", "landfill"):
        repository.save_scan(
            ScanRecord(item="x", category=category, region="Dortmund", confidence=0.9)
        )

    analytics = AnalyticsService(repository)
    assert analytics.total_scans("Dortmund") == 3
    assert analytics.recycling_rate("Dortmund") == 66.7
