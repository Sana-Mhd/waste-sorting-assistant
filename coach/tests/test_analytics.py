"""The analytics: the numbers behind the dashboard."""
import pandas as pd
import pytest

from coach import AnalyticsService, Summary


def test_the_frame_has_one_row_per_scan(dal):
    data = AnalyticsService(dal).frame("DO")
    assert len(data) == 9
    assert list(data.columns) == ["id", "item", "category", "confidence", "region_code", "created_at"]


def test_an_empty_database_gives_an_empty_frame(empty_dal):
    data = AnalyticsService(empty_dal).frame("DO")
    assert data.empty
    assert "category" in data.columns, "the columns must exist even with no rows"


def test_the_composition_adds_up_to_one_hundred(dal):
    shares = AnalyticsService(dal).composition("DO")
    assert set(shares) == {"recyclable", "compostable", "landfill"}
    # rounding each share to one decimal can lose a tenth in total
    assert abs(sum(shares.values()) - 100.0) <= 0.5


def test_the_composition_matches_the_data(dal):
    shares = AnalyticsService(dal).composition("DO")
    assert shares["recyclable"] == 55.6   # 5 of 9
    assert shares["compostable"] == 22.2  # 2 of 9
    assert shares["landfill"] == 22.2     # 2 of 9


def test_the_recycling_rate_counts_recyclable_and_compostable(dal):
    # 7 of 9 scans were recyclable or compostable
    assert AnalyticsService(dal).recycling_rate("DO") == 77.8


def test_the_average_confidence_is_a_percentage(dal):
    rate = AnalyticsService(dal).average_confidence("DO")
    assert 0 < rate <= 100


def test_everything_is_zero_without_data(empty_dal):
    analytics = AnalyticsService(empty_dal)
    assert analytics.total_scans("DO") == 0
    assert analytics.recycling_rate("DO") == 0.0
    assert analytics.average_confidence("DO") == 0.0
    assert analytics.composition("DO") == {}


def test_the_trend_has_one_row_per_day(dal):
    trend = AnalyticsService(dal).trend("DO", days=7)
    assert len(trend) == 7
    assert list(trend.columns) == ["date", "scans", "recycled"]


def test_the_trend_counts_the_scans_of_each_day(dal):
    trend = AnalyticsService(dal).trend("DO", days=3)
    assert trend["scans"].tolist() == [3, 3, 3]
    assert trend["scans"].sum() == 9


def test_a_day_without_scans_is_a_zero(dal):
    trend = AnalyticsService(dal).trend("DO", days=10)
    assert (trend["scans"] == 0).sum() == 7, "the seven days before the first scan"
    assert trend["scans"].sum() == 9


def test_the_trend_rejects_a_zero_day_window(dal):
    with pytest.raises(ValueError):
        AnalyticsService(dal).trend("DO", days=0)


def test_the_trend_is_empty_without_data(empty_dal):
    trend = AnalyticsService(empty_dal).trend("DO")
    assert trend.empty


def test_the_top_items_are_sorted(dal):
    top = AnalyticsService(dal).top_items("DO", limit=3)
    assert top.iloc[0]["item"] == "plastic bottle"
    assert top.iloc[0]["scans"] == 3
    assert len(top) == 3


def test_the_summary_collects_every_headline_number(dal):
    summary = AnalyticsService(dal).summary("DO")

    assert isinstance(summary, Summary)
    assert summary.total_scans == 9
    assert summary.recycling_rate == 77.8
    assert summary.region_code == "DO"
    assert abs(sum(summary.composition.values()) - 100.0) <= 0.5


def test_the_summary_of_an_empty_region_is_zero(empty_dal):
    summary = AnalyticsService(empty_dal).summary("DO")
    assert summary.total_scans == 0
    assert summary.composition == {}


def test_another_region_has_no_scans(dal):
    assert AnalyticsService(dal).total_scans("K") == 0
