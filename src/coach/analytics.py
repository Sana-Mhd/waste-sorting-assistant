"""Subsystem 3 - analytics behind the municipality dashboard.

OWNER: <name>

Contract with the rest of the team
----------------------------------
    AnalyticsService.composition(region) -> dict[str, float]
    AnalyticsService.recycling_rate(region) -> float
    AnalyticsService.trend(region, days) -> pandas.DataFrame

This half of subsystem 3 has nothing to do with the language model.  It only
reads scan records from subsystem 2 and turns them into numbers and charts.
"""

from __future__ import annotations

import pandas as pd

from ..data import Repository

RECYCLED_CATEGORIES = ("recyclable", "compostable")


class AnalyticsService:
    """Statistics over everything the users have scanned."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    # --- turning records into a table --------------------------------------

    def frame(self, region: str | None = None) -> pd.DataFrame:
        """All scans as a pandas DataFrame - the basis of every statistic."""
        scans = self.repository.all_scans(region)
        if not scans:
            return pd.DataFrame(columns=["item", "category", "region", "confidence", "created_at"])
        return pd.DataFrame(
            [
                {
                    "item": scan.item,
                    "category": scan.category,
                    "region": scan.region,
                    "confidence": scan.confidence,
                    "created_at": scan.created_at,
                }
                for scan in scans
            ]
        )

    # --- the public contract -------------------------------------------------

    def composition(self, region: str | None = None) -> dict[str, float]:
        """Share of each category, in percent."""
        data = self.frame(region)
        if data.empty:
            return {}
        shares = data["category"].value_counts(normalize=True) * 100
        return {category: round(value, 1) for category, value in shares.items()}

    def recycling_rate(self, region: str | None = None) -> float:
        """Percentage of scans that were recyclable or compostable."""
        data = self.frame(region)
        if data.empty:
            return 0.0
        recycled = data["category"].isin(RECYCLED_CATEGORIES).sum()
        return round(recycled / len(data) * 100, 1)

    def trend(self, region: str | None = None, days: int = 14) -> pd.DataFrame:
        """Number of scans per day over the last `days` days."""
        data = self.frame(region)
        if data.empty:
            return pd.DataFrame(columns=["date", "scans"])

        data["date"] = pd.to_datetime(data["created_at"]).dt.date
        counts = data.groupby("date").size().reset_index(name="scans")
        return counts.tail(days)

    def total_scans(self, region: str | None = None) -> int:
        return len(self.frame(region))
