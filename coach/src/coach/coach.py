"""The AI coach: the entry point of subsystem 3 for one classified item.

The coach does not know how the photo was classified and does not know how the
rules are stored. It asks subsystem 2 for the rule, looks in its own cache, and
only then asks the language model.
"""
from __future__ import annotations

import logging

from .cache import BaseCache, MemoryCache, SQLiteCache, make_key
from .config import CoachConfig
from .exceptions import CacheUnavailable, LanguageModelUnavailable
from .explainers import BaseExplainer, LanguageModelExplainer, TemplateExplainer
from .schemas import Explanation

logger = logging.getLogger(__name__)


class CoachService:
    """Produces the educational text shown next to the classification result."""

    def __init__(
        self,
        rule_engine,
        cache: BaseCache | None = None,
        explainer: BaseExplainer | None = None,
        fallback: BaseExplainer | None = None,
        config: CoachConfig | None = None,
    ) -> None:
        """
        Args:
            rule_engine: a data_rules.RuleEngine (subsystem 2).
            cache: where finished explanations are stored.
            explainer: the preferred explainer, by default the language model.
            fallback: used whenever the preferred one is unavailable.
            config: settings; read from the environment when not given.
        """
        self.config = config or CoachConfig.from_env()
        self.rules = rule_engine
        self.cache = cache if cache is not None else self._default_cache()
        self.explainer = explainer or LanguageModelExplainer(config=self.config)
        self.fallback = fallback or TemplateExplainer(self.config.language, self.config.max_words)

    def _default_cache(self) -> BaseCache:
        """A database-backed cache, or an in-memory one when the file cannot be opened."""
        try:
            return SQLiteCache(self.config.cache_path)
        except CacheUnavailable:
            logger.warning("Falling back to an in-memory cache")
            return MemoryCache()

    # --- the public contract ------------------------------------------------

    def explain(self, item: str, category: str, region_code: str) -> Explanation:
        """Explain where `item` belongs in `region_code`.

        Never raises because of the language model: when it cannot be reached,
        the text is built from the local rule instead.

        Args:
            item: what subsystem 1 recognised, e.g. "plastic bottle".
            category: "recyclable", "compostable" or "landfill".
            region_code: short region code, e.g. "DO".

        Raises:
            ValueError: unknown category (that is a bug in the caller).
        """
        item = item.strip()
        if not item:
            raise ValueError("item must not be empty")

        # Subsystem 2 validates the category and always returns a rule.
        rule = self.rules.get_rule(category, region_code)

        key = make_key(item, category, rule.region_code, self.config.language)
        stored = self.cache.get(key)
        if stored is not None:
            return self._wrap(stored, rule, source="cache")

        text, source = self._generate(item, rule)
        self.cache.set(key, text)
        return self._wrap(text, rule, source=source)

    def status(self) -> dict:
        """A short report the web interface can show, e.g. in a sidebar."""
        return {
            "explainer": type(self.explainer).__name__,
            "language_model_available": self.explainer.is_available(),
            "fallback": type(self.fallback).__name__,
            "cache": type(self.cache).__name__,
            "cached_explanations": len(self.cache),
            "language": self.config.language,
            "max_words": self.config.max_words,
        }

    def explain_result(self, result, region_code: str) -> Explanation:
        """Convenience for the web interface: takes the object subsystem 1 returns.

        Args:
            result: a classification.ClassificationResult.
        """
        return self.explain(result.material, result.category, region_code)

    # --- private helpers -------------------------------------------------------

    def _generate(self, item: str, rule) -> tuple[str, str]:
        """Ask the preferred explainer, fall back to the template on any failure."""
        if self.explainer.is_available():
            try:
                return self.explainer.explain(item, rule), self.explainer.source
            except LanguageModelUnavailable as exc:
                logger.warning("Explainer unavailable (%s), using the template", exc)
        return self.fallback.explain(item, rule), self.fallback.source

    def _wrap(self, text: str, rule, source: str) -> Explanation:
        """Put the text together with the bin and category into one Explanation."""
        return Explanation(
            text=text,
            bin=rule.bin,
            category=rule.category,
            region_code=rule.region_code,
            source=source,
        )
