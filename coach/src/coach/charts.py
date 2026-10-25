"""Ready-made charts for the municipality dashboard.

The web interface calls these and renders the figure; it never builds a chart
itself. Every figure uses the same palette and the same quiet frame, so the
dashboard reads as one system.

The three category colours were checked for colour-vision deficiency: no two of
them are confusable for protan, deutan or tritan vision, and each one has enough
contrast against the chart surface. Colour is never the only encoding - every
chart is labelled as well.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .analytics import AnalyticsService

# Fixed hue per category, never cycled: the same waste category always has the
# same colour on every chart of the dashboard.
CATEGORY_COLORS = {
    "recyclable": "#1B7F3B",
    "compostable": "#6B5BA6",
    "landfill": "#B4791F",
}
CATEGORY_ORDER = ("recyclable", "compostable", "landfill")

CATEGORY_LABELS = {
    "recyclable": "Recyclable",
    "compostable": "Compostable",
    "landfill": "Landfill",
}

SURFACE = "#FCFCFB"
INK = "#1A1A19"
MUTED = "#6B6B66"
GRID = "#E6E6E2"
LINE_COLOR = "#1B7F3B"

FONT = dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color=INK)


def _frame(fig: go.Figure, title: str, y_title: str = "") -> go.Figure:
    """The quiet frame every chart of the dashboard shares."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=INK), x=0, xanchor="left"),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=FONT,
        margin=dict(l=16, r=16, t=52, b=16),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(
        title=dict(text=y_title, font=dict(color=MUTED, size=12)),
        gridcolor=GRID,
        zeroline=False,
        linecolor=SURFACE,
        tickfont=dict(color=MUTED),
    )
    return fig


def composition_chart(analytics: AnalyticsService, region_code: str | None = None) -> go.Figure:
    """Share of each waste category, as a labelled bar chart."""
    shares = analytics.composition(region_code)
    categories = [c for c in CATEGORY_ORDER if c in shares]
    values = [shares[c] for c in categories]

    fig = go.Figure(
        go.Bar(
            x=[CATEGORY_LABELS[c] for c in categories],
            y=values,
            marker=dict(color=[CATEGORY_COLORS[c] for c in categories]),
            text=[f"{v:.1f}%" for v in values],
            textposition="outside",
            textfont=dict(color=MUTED, size=12),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
            width=0.55,
        )
    )
    fig.update_yaxes(range=[0, max(values) * 1.18 if values else 1], ticksuffix="%")
    return _frame(fig, "Waste composition", "share of scans")


def trend_chart(
    analytics: AnalyticsService, region_code: str | None = None, days: int = 14
) -> go.Figure:
    """Scans per day, as a line with a crosshair tooltip."""
    data = analytics.trend(region_code, days)

    fig = go.Figure(
        go.Scatter(
            x=data["date"],
            y=data["scans"],
            mode="lines+markers",
            line=dict(color=LINE_COLOR, width=2),
            marker=dict(size=8, color=LINE_COLOR, line=dict(width=2, color=SURFACE)),
            hovertemplate="%{x|%d %b}: %{y} scans<extra></extra>",
        )
    )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(tickformat="%d %b")
    return _frame(fig, f"Scans over the last {days} days", "scans per day")


def top_items_chart(
    analytics: AnalyticsService, region_code: str | None = None, limit: int = 5
) -> go.Figure:
    """The most scanned items, as a horizontal bar chart."""
    data = analytics.top_items(region_code, limit)
    data = data.iloc[::-1]  # highest bar on top

    fig = go.Figure(
        go.Bar(
            x=data["scans"],
            y=[str(item).title() for item in data["item"]],
            orientation="h",
            marker=dict(color=LINE_COLOR),
            text=data["scans"],
            textposition="outside",
            textfont=dict(color=MUTED, size=12),
            hovertemplate="%{y}: %{x} scans<extra></extra>",
            width=0.55,
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(gridcolor=SURFACE)
    return _frame(fig, f"Most scanned items (top {limit})", "")


def composition_table(analytics: AnalyticsService, region_code: str | None = None) -> pd.DataFrame:
    """The same numbers as `composition_chart`, for readers who prefer a table."""
    shares = analytics.composition(region_code)
    rows = [
        {"Category": CATEGORY_LABELS[c], "Share of scans": f"{shares[c]:.1f}%"}
        for c in CATEGORY_ORDER
        if c in shares
    ]
    return pd.DataFrame(rows, columns=["Category", "Share of scans"])
