"""Subsystem 3 - the only place that talks to the language model.

Keeping the API behind one small class means a different provider can be
plugged in later without touching anything else.
"""

from __future__ import annotations

import os


class OpenAIClient:
    """Thin wrapper around the OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        # The key is read from the environment, never written into the code.
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        """True when a request can actually be sent."""
        return bool(self.api_key)

    def send(self, prompt: str) -> str:
        """Send one prompt and return the answer.

        TODO (subsystem 3): call the real API here, for example

            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            answer = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return answer.choices[0].message.content.strip()
        """
        raise NotImplementedError("the real API call is not wired up yet")
