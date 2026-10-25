"""The explanation cache.

The same item in the same region must not be paid for twice. BaseCache is the
abstract interface; MemoryCache keeps the answers in a dictionary and is used
by the tests, SQLiteCache keeps them in a small database file of its own and
is used by the application.

The cache has its own file on purpose. Subsystem 2 owns the project database,
and nobody outside that package talks to it directly.
"""
from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from .exceptions import CacheUnavailable

logger = logging.getLogger(__name__)


def make_key(item: str, category: str, region_code: str, language: str = "en") -> str:
    """The key under which one explanation is stored."""
    return "|".join(
        part.strip().lower() for part in (item, category, region_code, language)
    )


class BaseCache(ABC):
    """Interface every cache of the coach implements."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Return the stored text, or None when nothing is stored."""

    @abstractmethod
    def set(self, key: str, text: str) -> None:
        """Store one explanation."""

    @abstractmethod
    def __len__(self) -> int:
        """How many explanations are stored."""

    def clear(self) -> None:
        """Remove everything. Used by the tests and when a rule changes."""
        raise NotImplementedError


class MemoryCache(BaseCache):
    """Cache that lives only as long as the program runs."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, text: str) -> None:
        self._store[key] = text

    def __len__(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()


class SQLiteCache(BaseCache):
    """Cache that survives a restart, in its own small database file."""

    _CREATE = """
        CREATE TABLE IF NOT EXISTS explanation_cache (
            key        TEXT PRIMARY KEY,
            text       TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        try:
            if self.path.parent != Path(""):
                self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute(self._CREATE)
        except (sqlite3.Error, OSError) as exc:
            raise CacheUnavailable(f"cannot open the cache at {self.path}") from exc

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, key: str) -> str | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT text FROM explanation_cache WHERE key = ?", (key,)
                ).fetchone()
        except sqlite3.Error:
            logger.warning("Cache read failed for %s, continuing without it", key)
            return None
        return row[0] if row else None

    def set(self, key: str, text: str) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO explanation_cache (key, text, created_at)"
                    " VALUES (?, ?, ?)",
                    (key, text, now),
                )
        except sqlite3.Error:
            logger.warning("Cache write failed for %s, continuing without it", key)

    def __len__(self) -> int:
        try:
            with self._connect() as conn:
                return conn.execute("SELECT COUNT(*) FROM explanation_cache").fetchone()[0]
        except sqlite3.Error:
            return 0

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM explanation_cache")
