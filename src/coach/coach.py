"""Subsystem 3 - AI Coach.

OWNER: <name>

Contract with the rest of the team
----------------------------------
    CoachService.explain(item, region) -> str

The coach turns a classified item plus its local rule into a short piece of
plain language the user can learn from.  It never raises: if the language
model cannot be reached, a stored fallback text is returned instead, so the
application keeps working.
"""

from __future__ import annotations

from ..data import Repository
from .cache import ExplanationCache
from .client import OpenAIClient

MAX_WORDS = 60


class CoachService:
    """Produces the educational explanation shown next to the result."""

    def __init__(
        self,
        repository: Repository,
        cache: ExplanationCache | None = None,
        client: OpenAIClient | None = None,
    ) -> None:
        self.repository = repository
        self.cache = cache or ExplanationCache()
        self.client = client or OpenAIClient()

    # --- the public contract ---------------------------------------------

    def explain(self, item: str, region: str) -> str:
        """Return a short explanation of where `item` goes in `region`."""
        key = self.cache.make_key(item, region)

        stored = self.cache.get(key)
        if stored is not None:
            return stored

        rule = self._rule_for(item, region)

        if self.client.is_available():
            try:
                text = self.client.send(self._build_prompt(item, rule))
            except Exception:
                text = self._fallback(item, rule)
        else:
            text = self._fallback(item, rule)

        self.cache.set(key, text)
        return text

    # --- private helpers ---------------------------------------------------

    def _rule_for(self, item: str, region: str):
        """Look the local rule up through subsystem 2."""
        from ..classification import classify  # local import avoids a cycle

        # The web interface already knows the category; this fallback keeps
        # `explain` usable on its own.
        category = classify(item).category
        return self.repository.get_rule(category, region)

    def _build_prompt(self, item: str, rule) -> str:
        return (
            f"You are a friendly recycling coach in {rule.region}, Germany.\n"
            f"A resident wants to dispose of: {item}.\n"
            f"The local rule says it belongs in the {rule.bin_name} "
            f"({rule.bin_color} bin). {rule.note}\n"
            f"Explain in at most {MAX_WORDS} words, in simple language, "
            f"why it belongs there and how to prepare it."
        )

    def _fallback(self, item: str, rule) -> str:
        """Used when the language model is unavailable."""
        note = f" {rule.note}" if rule.note else ""
        return (
            f"In {rule.region}, {item} belongs in the {rule.bin_name} "
            f"({rule.bin_color} bin).{note}"
        )
