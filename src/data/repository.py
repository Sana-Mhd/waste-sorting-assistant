"""Subsystem 2 - Data & Rules.

OWNER: <name>

Contract with the rest of the team
----------------------------------
    Repository.get_rule(category, region) -> Rule
    Repository.save_scan(record) -> None
    Repository.all_scans(region=None) -> list[ScanRecord]

Nobody outside this module touches the database directly.  Everything goes
through a Repository object.

Right now the rules live in a dictionary and the scans in a list, so the
application already runs.  Replace the bodies with SQLAlchemy and SQLite.
"""

from __future__ import annotations

from .models import Rule, ScanRecord

# --- temporary rule table ----------------------------------------------------
# TODO (subsystem 2): move this into the database, one row per rule,
# and add at least one more region.
_RULES: dict[tuple[str, str], Rule] = {
    ("recyclable", "Dortmund"): Rule(
        category="recyclable",
        region="Dortmund",
        bin_name="Gelbe Tonne",
        bin_color="yellow",
        note="Packaging made of plastic, metal or composite material.",
    ),
    ("compostable", "Dortmund"): Rule(
        category="compostable",
        region="Dortmund",
        bin_name="Biotonne",
        bin_color="brown",
        note="Food and garden waste, no plastic bags.",
    ),
    ("landfill", "Dortmund"): Rule(
        category="landfill",
        region="Dortmund",
        bin_name="Restmülltonne",
        bin_color="grey",
        note="Everything that cannot be recycled or composted.",
    ),
}

REGIONS = ["Dortmund"]


class RuleNotFound(Exception):
    """Raised when no rule exists for this category in this region."""


class Repository:
    """The single door to the stored data."""

    def __init__(self, database_url: str | None = None) -> None:
        # TODO (subsystem 2): open the real database connection here.
        self._database_url = database_url
        self._scans: list[ScanRecord] = []

    # --- rules ---------------------------------------------------------

    def get_rule(self, category: str, region: str) -> Rule:
        """Return the bin that `category` goes into in `region`."""
        try:
            return _RULES[(category, region)]
        except KeyError as exc:
            raise RuleNotFound(f"no rule for {category!r} in {region!r}") from exc

    def regions(self) -> list[str]:
        return list(REGIONS)

    # --- scans ---------------------------------------------------------

    def save_scan(self, record: ScanRecord) -> None:
        """Store one scan so the analytics can count it later."""
        self._scans.append(record)

    def all_scans(self, region: str | None = None) -> list[ScanRecord]:
        if region is None:
            return list(self._scans)
        return [scan for scan in self._scans if scan.region == region]
