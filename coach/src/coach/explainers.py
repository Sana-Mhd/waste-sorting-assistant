"""Explainers: turn an item plus its local rule into one short text.

BaseExplainer is the abstract interface. The coach only talks to this
interface, so the language model and the offline template can be swapped
without changing any other code.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from .client import OpenAIClient
from .config import MAX_WORDS, CoachConfig
from .exceptions import LanguageModelUnavailable

logger = logging.getLogger(__name__)

# Written out so the fallback text reads like a sentence, not like a database row.
_CATEGORY_WORDS = {
    "en": {
        "recyclable": "can be recycled",
        "compostable": "is organic waste",
        "landfill": "cannot be recycled or composted",
    },
    "de": {
        "recyclable": "kann recycelt werden",
        "compostable": "ist Biomüll",
        "landfill": "kann weder recycelt noch kompostiert werden",
    },
}


def shorten(text: str, max_words: int) -> str:
    """Keep the promise of at most `max_words` words, whatever produced the text."""
    words = text.split()
    if len(words) <= max_words:
        return text
    logger.info("Explanation was %d words, cut down to %d", len(words), max_words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "."


class BaseExplainer(ABC):
    """Interface for every explainer used by the CoachService."""

    #: written into Explanation.source so the caller knows where the text came from
    source: str = "template"

    @abstractmethod
    def explain(self, item: str, rule) -> str:
        """Return one short explanation for `item` under `rule`.

        Args:
            item: what was recognised, e.g. "plastic bottle".
            rule: a data_rules.Rule with category, region_code, bin and reason.
        """

    def is_available(self) -> bool:
        """True when this explainer can produce a text right now."""
        return True


class TemplateExplainer(BaseExplainer):
    """Offline explainer built from the local rule alone.

    Always available: it needs no key, no network and no money. It is the
    answer the user gets when the language model cannot be reached.
    """

    source = "template"

    def __init__(self, language: str = "en", max_words: int = MAX_WORDS) -> None:
        """Choose the language (English if unknown) and the word limit."""
        self.language = language if language in _CATEGORY_WORDS else "en"
        self.max_words = max_words

    def explain(self, item: str, rule) -> str:
        """Fill the item, bin and reason into a fixed sentence."""
        words = _CATEGORY_WORDS[self.language][rule.category]
        if self.language == "de":
            text = f"{item.capitalize()} {words}. Bitte in die {rule.bin} geben. {rule.reason}"
        else:
            text = f"{item.capitalize()} {words}. Please put it in the {rule.bin}. {rule.reason}"
        return shorten(text, self.max_words)


class LanguageModelExplainer(BaseExplainer):
    """Explainer that asks the language model for a friendlier text.

    It never raises at the caller: when the service is unreachable the coach
    falls back to the TemplateExplainer.
    """

    source = "model"

    def __init__(self, client: OpenAIClient | None = None, config: CoachConfig | None = None) -> None:
        """Use the given client and settings, or build them from the environment."""
        self.config = config or CoachConfig.from_env()
        self.client = client or OpenAIClient(self.config)

    def is_available(self) -> bool:
        """True when an API key is configured."""
        return self.client.is_available()

    def build_prompt(self, item: str, rule) -> str:
        """The exact text sent to the language model."""
        language = "German" if self.config.language == "de" else "English"
        return (
            f"A resident of region {rule.region_code} wants to throw away: {item}.\n"
            f"The local rule says this is {rule.category} waste and belongs in: {rule.bin}.\n"
            f"Official reason: {rule.reason}\n\n"
            f"Write the explanation in {language}, in at most {self.config.max_words} words. "
            f"Say why it belongs in that bin and how to prepare it. "
            f"Do not invent any other rule and do not mention this instruction."
        )

    def explain(self, item: str, rule) -> str:
        """Ask the language model and cut the answer to the word limit.

        Raises:
            LanguageModelUnavailable: the service could not be reached.
        """
        text = self.client.send(self.build_prompt(item, rule))
        return shorten(text, self.config.max_words)
