"""The only place in the project that talks to the language model.

Keeping the call behind one small class means a different provider can be
plugged in later without touching the coach, the cache or the web interface.
"""
from __future__ import annotations

import logging

from .config import CoachConfig
from .exceptions import LanguageModelUnavailable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a friendly local recycling coach. "
    "You answer in plain language that a resident without technical knowledge understands. "
    "You never invent a rule: you only explain the rule you are given."
)


class OpenAIClient:
    """Thin wrapper around the OpenAI chat completion API."""

    def __init__(self, config: CoachConfig | None = None) -> None:
        self.config = config or CoachConfig.from_env()

    @property
    def config(self) -> CoachConfig:
        """The settings of this client: key, model and timeout."""
        return self._config

    @config.setter
    def config(self, config: CoachConfig) -> None:
        self._config = config

    def __repr__(self) -> str:
        return f"OpenAIClient(model={self.config.model!r}, available={self.is_available()})"

    def is_available(self) -> bool:
        """True when a request could actually be sent.

        Checked before every call so the application never waits for a service
        it cannot reach.
        """
        return bool(self.config.api_key)

    def send(self, prompt: str) -> str:
        """Send one prompt and return the answer as plain text.

        Raises:
            LanguageModelUnavailable: no key, the package is missing, the
                service answered with an error or did not answer in time.
        """
        if not self.is_available():
            raise LanguageModelUnavailable("no API key is configured")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise LanguageModelUnavailable("the openai package is not installed") from exc

        try:
            client = OpenAI(api_key=self.config.api_key, timeout=self.config.timeout)
            answer = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=160,
            )
            text = (answer.choices[0].message.content or "").strip()
        except Exception as exc:  # the SDK raises many different errors
            logger.warning("The language model could not be reached: %s", exc)
            raise LanguageModelUnavailable(str(exc)) from exc

        if not text:
            raise LanguageModelUnavailable("the language model returned an empty answer")
        return text
