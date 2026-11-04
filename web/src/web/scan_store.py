"""Remembers the latest scans, so the result page can be opened again without a new scan.

After an upload the browser is sent to a normal result page. Reloading that page only
reads the scan from this store, so one upload is always saved exactly once.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from .workflow import ScanOutcome

DEFAULT_MAX_SCANS = 20


@dataclass(frozen=True)
class StoredScan:
    """One finished scan and the photo that belongs to it."""

    outcome: ScanOutcome
    photo: bytes


class ScanStore:
    """Keeps the newest scans in memory; the oldest is dropped when the store is full.

    The permanent record of a scan is in data_rules. This store only serves the result
    page, so it is fine that it is empty again after a restart.
    """

    def __init__(self, max_scans: int = DEFAULT_MAX_SCANS) -> None:
        if max_scans < 1:
            raise ValueError(f"max_scans must be at least 1, got {max_scans}.")
        self._max_scans = max_scans
        self._scans: OrderedDict[str, StoredScan] = OrderedDict()
        self._lock = Lock()   # the server answers several requests at the same time

    def add(self, outcome: ScanOutcome, photo: bytes) -> str:
        """Store a scan and return the id for its result page."""
        scan_id = uuid4().hex
        with self._lock:
            self._scans[scan_id] = StoredScan(outcome, photo)
            while len(self._scans) > self._max_scans:
                self._scans.popitem(last=False)
        return scan_id

    def get(self, scan_id: str | None) -> StoredScan | None:
        """Return a stored scan, or None if the id is unknown or the scan was dropped."""
        if scan_id is None:
            return None
        with self._lock:
            return self._scans.get(scan_id)
