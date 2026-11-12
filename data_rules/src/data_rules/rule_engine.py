"""Rule matching: (category, region) -> Rule."""
import logging

from .config import CATEGORIES
from .data_access import DataAccessLayer
from .exceptions import DataRulesError
from .schemas import Rule

log = logging.getLogger(__name__)

# Used only when a region has no rule for a category, so the app never crashes.
_FALLBACK = {
    "recyclable": ("Recycling collection", "This item can be recycled. Check your local rules for the exact bin."),
    "compostable": ("Organic waste bin", "This item is organic and can be composted."),
    "landfill": ("General waste bin", "This item cannot be recycled or composted."),
}


class RuleEngine:
    """Finds the right bin for a category in a region, with a safe fallback."""

    def __init__(self, dal: DataAccessLayer):
        """Keep the data access layer that stores the rules."""
        self._dal = dal

    def get_rule(self, category: str, region: str) -> Rule:
        """Return the bin for this category in this region.

        Raises DataRulesError (a ValueError) for an unknown category, because
        that is a bug in the caller. For an unknown region or a missing rule it
        returns a generic fallback and logs a warning, so the user still gets an answer.
        """
        if category not in CATEGORIES:
            raise DataRulesError(f"category must be one of {CATEGORIES}, got {category!r}")
        rule = self._dal.get_rule(category, region)
        if rule is not None:
            return rule
        log.warning("No rule for category=%s region=%s, using fallback", category, region)
        bin_name, reason = _FALLBACK[category]
        return Rule(category=category, region_code=region.strip().upper(), bin=bin_name, reason=reason)
