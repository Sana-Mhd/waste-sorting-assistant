import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# data_rules is imported by the contract test (categories and field names must match).
sys.path.insert(0, str(ROOT.parent / "data_rules" / "src"))


# --- stand-ins for subsystem 2, so these tests need no database ---------------


@dataclass(frozen=True)
class FakeRule:
    category: str
    region_code: str
    bin: str
    reason: str


@dataclass(frozen=True)
class FakeRecord:
    id: int
    item: str
    category: str
    confidence: float
    region_code: str
    created_at: datetime


class FakeRuleEngine:
    """Behaves like data_rules.RuleEngine: valid category in, Rule out."""

    CATEGORIES = ("recyclable", "compostable", "landfill")
    BINS = {
        "recyclable": "Yellow bin (Wertstofftonne)",
        "compostable": "Brown bin (Biotonne)",
        "landfill": "Grey bin (Restmülltonne)",
    }

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_rule(self, category: str, region: str) -> FakeRule:
        if category not in self.CATEGORIES:
            raise ValueError(f"category must be one of {self.CATEGORIES}, got {category!r}")
        self.calls.append((category, region))
        return FakeRule(
            category=category,
            region_code=region.strip().upper(),
            bin=self.BINS[category],
            reason="Local rule for this category.",
        )


class FakeDataAccess:
    """Behaves like data_rules.DataAccessLayer for the two methods analytics uses."""

    def __init__(self, records: list[FakeRecord] | None = None) -> None:
        self.records = records or []

    def get_results(self, region_code=None, since=None, until=None) -> list[FakeRecord]:
        rows = self.records
        if region_code:
            rows = [r for r in rows if r.region_code == region_code.strip().upper()]
        if since:
            rows = [r for r in rows if r.created_at >= since]
        if until:
            rows = [r for r in rows if r.created_at <= until]
        return list(rows)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """No test may write into the project folder.

    Anything built from the environment gets a cache file inside the temporary
    directory pytest creates, so a test run leaves nothing behind.
    """
    monkeypatch.setenv("COACH_CACHE_PATH", str(tmp_path / "coach_cache.db"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def rule_engine() -> FakeRuleEngine:
    return FakeRuleEngine()


@pytest.fixture
def records() -> list[FakeRecord]:
    """Nine scans over three days: 5 recyclable, 2 compostable, 2 landfill."""
    day = datetime(2026, 10, 20, 9, 0)
    plan = [
        ("plastic bottle", "recyclable", 0.93, 0),
        ("glass jar", "recyclable", 0.88, 0),
        ("banana peel", "compostable", 0.95, 0),
        ("plastic bottle", "recyclable", 0.91, 1),
        ("coffee grounds", "compostable", 0.84, 1),
        ("ceramic cup", "landfill", 0.72, 1),
        ("plastic bottle", "recyclable", 0.90, 2),
        ("metal can", "recyclable", 0.87, 2),
        ("diaper", "landfill", 0.69, 2),
    ]
    return [
        FakeRecord(
            id=i + 1,
            item=item,
            category=category,
            confidence=confidence,
            region_code="DO",
            created_at=day + timedelta(days=offset, minutes=i),
        )
        for i, (item, category, confidence, offset) in enumerate(plan)
    ]


@pytest.fixture
def dal(records) -> FakeDataAccess:
    return FakeDataAccess(records)


@pytest.fixture
def empty_dal() -> FakeDataAccess:
    return FakeDataAccess([])
