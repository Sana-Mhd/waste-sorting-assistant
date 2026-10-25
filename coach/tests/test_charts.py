"""The dashboard charts: every figure is built and carries its data."""
import plotly.graph_objects as go

from coach import AnalyticsService, charts


def test_every_category_has_its_own_fixed_colour():
    colours = set(charts.CATEGORY_COLORS.values())
    assert len(colours) == 3, "two categories share a colour"
    assert set(charts.CATEGORY_COLORS) == set(charts.CATEGORY_ORDER)


def test_the_composition_chart_shows_one_bar_per_category(dal):
    figure = charts.composition_chart(AnalyticsService(dal), "DO")

    assert isinstance(figure, go.Figure)
    bar = figure.data[0]
    assert len(bar.x) == 3
    assert bar.text, "the bars are labelled, so colour is not the only encoding"


def test_the_trend_chart_has_one_point_per_day(dal):
    figure = charts.trend_chart(AnalyticsService(dal), "DO", days=7)
    assert len(figure.data[0].x) == 7


def test_the_top_items_chart_is_horizontal(dal):
    figure = charts.top_items_chart(AnalyticsService(dal), "DO", limit=3)
    assert figure.data[0].orientation == "h"


def test_the_charts_survive_an_empty_database(empty_dal):
    analytics = AnalyticsService(empty_dal)
    assert isinstance(charts.composition_chart(analytics, "DO"), go.Figure)
    assert isinstance(charts.trend_chart(analytics, "DO"), go.Figure)
    assert isinstance(charts.top_items_chart(analytics, "DO"), go.Figure)


def test_the_table_view_repeats_the_numbers_of_the_chart(dal):
    analytics = AnalyticsService(dal)
    table = charts.composition_table(analytics, "DO")

    assert list(table.columns) == ["Category", "Share of scans"]
    assert len(table) == 3
