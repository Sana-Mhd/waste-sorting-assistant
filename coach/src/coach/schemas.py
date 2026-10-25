"""Plain data objects that cross the subsystem boundary.

The web interface receives these, never an OpenAI response object or a
pandas row, so nobody outside this package needs to know how the coach works.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Explanation:
    """The answer of the AI coach for one classified item."""

    text: str           # the sentence shown to the user
    bin: str            # the bin the local rule points at
    category: str       # "recyclable" | "compostable" | "landfill"
    region_code: str    # e.g. "DO"
    source: str         # "model" | "cache" | "template"

    @property
    def from_language_model(self) -> bool:
        return self.source == "model"


@dataclass(frozen=True)
class Summary:
    """The numbers shown on the municipality dashboard."""

    region_code: str | None
    total_scans: int
    recycling_rate: float               # percent, 0..100
    composition: dict[str, float] = field(default_factory=dict)   # percent per category
    average_confidence: float = 0.0     # percent, 0..100
