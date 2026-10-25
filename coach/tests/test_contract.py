"""Contract checks against subsystem 2.

These tests fail the moment subsystem 2 renames a field or adds a category, so
the mismatch is found by pytest and not by a user.
"""
import pytest

data_rules = pytest.importorskip(
    "data_rules", reason="subsystem 2 is not on the path in this environment"
)

from coach import RECYCLED_CATEGORIES, charts  # noqa: E402
from coach.cache import make_key  # noqa: E402


def test_the_categories_are_the_ones_subsystem_two_knows():
    assert set(charts.CATEGORY_ORDER) == set(data_rules.CATEGORIES)


def test_every_recycled_category_is_a_real_category():
    for category in RECYCLED_CATEGORIES:
        assert category in data_rules.CATEGORIES


def test_the_rule_still_has_the_fields_the_coach_reads():
    fields = data_rules.Rule.__dataclass_fields__
    for name in ("category", "region_code", "bin", "reason"):
        assert name in fields, f"subsystem 2 renamed Rule.{name}"


def test_the_record_still_has_the_fields_the_analytics_read():
    fields = data_rules.ClassificationRecord.__dataclass_fields__
    for name in ("id", "item", "category", "confidence", "region_code", "created_at"):
        assert name in fields, f"subsystem 2 renamed ClassificationRecord.{name}"


def test_the_coach_works_on_the_real_rule_engine(tmp_path):
    """End to end against the real database of subsystem 2, without a network call."""
    from coach import CoachConfig, CoachService, MemoryCache, TemplateExplainer

    dal, engine = data_rules.create_services(f"sqlite:///{tmp_path/'test.db'}")
    coach = CoachService(
        engine,
        cache=MemoryCache(),
        explainer=TemplateExplainer(),
        config=CoachConfig(api_key=""),
    )

    answer = coach.explain("plastic bottle", "recyclable", "DO")

    assert answer.text
    assert answer.bin
    assert answer.region_code == "DO"


def test_the_analytics_work_on_the_real_data_access(tmp_path):
    from coach import AnalyticsService

    dal, _engine = data_rules.create_services(f"sqlite:///{tmp_path/'test.db'}")
    dal.save_result("plastic bottle", "recyclable", 0.93, "DO")
    dal.save_result("banana peel", "compostable", 0.88, "DO")
    dal.save_result("ceramic cup", "landfill", 0.71, "DO")

    analytics = AnalyticsService(dal)

    assert analytics.total_scans("DO") == 3
    assert analytics.recycling_rate("DO") == 66.7
    # rounding each share to one decimal can lose a tenth in total
    assert abs(sum(analytics.composition("DO").values()) - 100.0) <= 0.5


def test_the_cache_key_uses_the_region_code_of_subsystem_two():
    assert make_key("plastic bottle", "recyclable", "DO") == "plastic bottle|recyclable|do|en"
