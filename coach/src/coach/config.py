"""Settings of the AI coach, read from the environment.

Nothing secret is written into the code: the API key comes from the
environment variable OPENAI_API_KEY, which Docker and the .env file provide.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# An explanation longer than this is not read by anybody.
MAX_WORDS = 60

# Where the explanation cache keeps its own small database.
DEFAULT_CACHE_URL = "data/coach_cache.db"

# Seconds to wait for the language model before giving up and using a template.
DEFAULT_TIMEOUT = 10.0

DEFAULT_MODEL = "gpt-4o-mini"

# The two languages the application supports.
LANGUAGES = ("en", "de")


@dataclass(frozen=True)
class CoachConfig:
    """Everything the coach needs to know at start-up.

    The API key is held here but never printed: `__repr__` masks it, so the key
    cannot leak into a log line, a traceback or a web error page.
    """

    api_key: str = ""
    model: str = DEFAULT_MODEL
    cache_path: str = DEFAULT_CACHE_URL
    timeout: float = DEFAULT_TIMEOUT
    max_words: int = MAX_WORDS
    language: str = "en"

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def __repr__(self) -> str:
        key = "set" if self.api_key else "missing"
        return (
            f"CoachConfig(api_key=<{key}>, model={self.model!r}, "
            f"cache_path={self.cache_path!r}, max_words={self.max_words}, "
            f"language={self.language!r})"
        )

    @classmethod
    def from_env(cls) -> "CoachConfig":
        """Build the configuration from environment variables."""
        language = os.getenv("COACH_LANGUAGE", "en").strip().lower()
        if language not in LANGUAGES:
            language = "en"
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            cache_path=os.getenv("COACH_CACHE_PATH", DEFAULT_CACHE_URL).strip(),
            timeout=float(os.getenv("COACH_TIMEOUT", DEFAULT_TIMEOUT)),
            max_words=int(os.getenv("COACH_MAX_WORDS", MAX_WORDS)),
            language=language,
        )
