"""Subsystem 2 - the shapes of the data everybody shares.

OWNER: <name>

These are plain dataclasses for now.  Subsystem 2 replaces them with real
SQLAlchemy models; the field names must stay the same, because the other
subsystems read them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Rule:
    """One local recycling rule: which bin a category goes into."""

    category: str      # recyclable / compostable / landfill
    region: str        # e.g. "Dortmund"
    bin_name: str      # e.g. "Gelbe Tonne"
    bin_color: str     # e.g. "yellow"
    note: str = ""     # short local remark, e.g. "rinse before disposal"


@dataclass
class ScanRecord:
    """One photo a user scanned.  The analytics are built from these rows."""

    item: str
    category: str
    region: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
