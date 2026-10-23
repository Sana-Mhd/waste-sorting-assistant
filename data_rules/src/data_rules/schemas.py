"""Plain data objects that cross the subsystem boundary.

Other subsystems receive these, never SQLAlchemy objects, so nobody outside
this package needs to know how the database is built.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Rule:
    category: str       # "recyclable" | "compostable" | "landfill"
    region_code: str    # e.g. "DO" for Dortmund
    bin: str            # name of the bin the user should use
    reason: str         # one short sentence why


@dataclass(frozen=True)
class ClassificationRecord:
    id: int
    item: str
    category: str
    confidence: float
    region_code: str
    created_at: datetime
