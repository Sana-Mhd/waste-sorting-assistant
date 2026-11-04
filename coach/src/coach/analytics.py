"""Analytics: the numbers behind the municipality dashboard.

This half of subsystem 3 has nothing to do with the language model. It reads
the stored classifications from subsystem 2 and turns them into statistics with
pandas and numpy.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .schemas import Summary

logger = logging.getLogger(__name__)

# What counts as "kept out of the residual waste".
RECYCLED_CATEGORIES = ("recyclable", "compostable")

COLUMNS = ["id", "item", "category", "confidence", "region_code", "created_at"]


class AnalyticsService:
    """Statistics over everything the users have scanned."""

    def __init__(self, data_access) -> None:
        """
        Args:
            data_access: a data_rules.DataAccessLayer (subsystem 2).
        """
        self.dal = data_access

    @property
    def dal(self):
        """The data_rules.DataAccessLayer (subsystem 2) that holds the scans."""
        return self._dal

    @dal.setter
    def dal(self, data_access) -> None:
        self._dal = data_access

    # --- from stored rows to a table ---------------------------------------

    def frame(
        self,
        region_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> pd.DataFrame:
        """Every stored classification as a DataFrame, the basis of all statistics."""
        records = self.dal.get_results(region_code=region_code, since=since, until=until)
        if not records:
            return pd.DataFrame(columns=COLUMNS)

        data = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "item": r.item,
                    "category": r.category,
                    "confidence": r.confidence,
                    "region_code": r.region_code,
                    "created_at": r.created_at,
                }
                for r in records
            ]
        )
        data["created_at"] = pd.to_datetime(data["created_at"])
        return data

    # --- the public contract -------------------------------------------------

    def composition(self, region_code: str | None = None) -> dict[str, float]:
        """Share of every category, in percent, rounded to one decimal."""
        data = self.frame(region_code)
        if data.empty:
            return {}
        shares = data["category"].value_counts(normalize=True) * 100
        return {str(category): round(float(value), 1) for category, value in shares.items()}

    def recycling_rate(self, region_code: str | None = None) -> float:
        """Percentage of scans that were recyclable or compostable."""
        data = self.frame(region_code)
        if data.empty:
            return 0.0
        recycled = data["category"].isin(RECYCLED_CATEGORIES).to_numpy()
        return round(float(np.mean(recycled) * 100), 1)

    def average_confidence(self, region_code: str | None = None) -> float:
        """How sure the classification engine was on average, in percent."""
        data = self.frame(region_code)
        if data.empty:
            return 0.0
        return round(float(np.mean(data["confidence"].to_numpy()) * 100), 1)

    def trend(self, region_code: str | None = None, days: int = 14) -> pd.DataFrame:
        """Scans per day over the last `days` days, with empty days filled in.

        Returns a DataFrame with the columns `date`, `scans` and `recycled`.
        """
        if days < 1:
            raise ValueError("days must be at least 1")

        data = self.frame(region_code)
        if data.empty:
            return pd.DataFrame(columns=["date", "scans", "recycled"])

        data["date"] = data["created_at"].dt.normalize()
        data["is_recycled"] = data["category"].isin(RECYCLED_CATEGORIES)

        grouped = (
            data.groupby("date")
            .agg(scans=("id", "count"), recycled=("is_recycled", "sum"))
            .reset_index()
        )

        # A day without any scan is a zero, not a missing row.
        last_day = data["date"].max()
        calendar = pd.date_range(end=last_day, periods=days, freq="D")
        grouped = (
            grouped.set_index("date")
            .reindex(calendar, fill_value=0)
            .rename_axis("date")
            .reset_index()
        )
        grouped["scans"] = grouped["scans"].astype(int)
        grouped["recycled"] = grouped["recycled"].astype(int)
        return grouped

    def top_items(self, region_code: str | None = None, limit: int = 5) -> pd.DataFrame:
        """The most frequently scanned items, with the columns `item` and `scans`."""
        data = self.frame(region_code)
        if data.empty:
            return pd.DataFrame(columns=["item", "scans"])
        counts = data["item"].value_counts().head(limit)
        return counts.rename_axis("item").reset_index(name="scans")

    def summary(self, region_code: str | None = None) -> Summary:
        """Every headline number of the dashboard in one object."""
        data = self.frame(region_code)
        if data.empty:
            return Summary(region_code=region_code, total_scans=0, recycling_rate=0.0)

        recycled = data["category"].isin(RECYCLED_CATEGORIES).to_numpy()
        shares = data["category"].value_counts(normalize=True) * 100
        return Summary(
            region_code=region_code,
            total_scans=int(len(data)),
            recycling_rate=round(float(np.mean(recycled) * 100), 1),
            composition={str(k): round(float(v), 1) for k, v in shares.items()},
            average_confidence=round(float(np.mean(data["confidence"].to_numpy()) * 100), 1),
        )

    def total_scans(self, region_code: str | None = None) -> int:
        return int(len(self.frame(region_code)))
