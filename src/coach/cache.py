"""Subsystem 3 - stored explanations.

Keeps answers that were already generated, so the same item in the same
region is never paid for twice.
"""

from __future__ import annotations


class ExplanationCache:
    """A small key-value store for finished explanations."""

    def __init__(self) -> None:
        # TODO: back this with the SQLite table `explanation_cache`
        # (key, text, created_at) instead of a dictionary in memory.
        self._store: dict[str, str] = {}

    @staticmethod
    def make_key(item: str, region: str) -> str:
        return f"{item.strip().lower()}|{region.strip().lower()}"

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, text: str) -> None:
        self._store[key] = text

    def __len__(self) -> int:
        return len(self._store)
