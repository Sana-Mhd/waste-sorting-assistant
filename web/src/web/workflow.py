"""One scan from photo to answer, without any web code.

Keeping the logic here (and the display in pages.py) means it can be tested with
plain pytest, and the page only has to show a ScanOutcome.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from classification import ClassificationResult
from coach import Explanation

from .services import AppServices

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanOutcome:
    """Everything the scan page needs to show for one photo."""

    result: ClassificationResult        # subsystem 1: material, category, confidence, top3
    explanation: Explanation | None     # subsystem 3: bin and text; None if not confident
    saved_id: int | None                # subsystem 2: row id; None if not stored

    @property
    def is_confident(self) -> bool:
        return self.result.is_confident

    @property
    def was_saved(self) -> bool:
        return self.saved_id is not None


class ScanWorkflow:
    """Classify a photo, explain the result and store it."""

    def __init__(self, services: AppServices) -> None:
        self.services = services

    @property
    def services(self) -> AppServices:
        """The services of subsystems 1-3 used for a scan."""
        return self._services

    @services.setter
    def services(self, services: AppServices) -> None:
        self._services = services

    def run(self, image: bytes, region_code: str) -> ScanOutcome:
        """Process one uploaded photo.

        Uncertain results are neither explained nor stored, so the dashboard
        only counts answers the user was actually shown.

        Args:
            image: the raw bytes of the upload.
            region_code: a code from data_rules, e.g. "DO".

        Raises:
            InvalidImageError: if the file is not a usable JPEG/PNG photo.
        """
        result = self.services.classifier.classify(image)
        if not result.is_confident:
            logger.info("Not confident (%s, %.2f): asking for a new photo", result.material, result.confidence)
            return ScanOutcome(result, explanation=None, saved_id=None)

        explanation = self.services.coach.explain_result(result, region_code)
        return ScanOutcome(result, explanation, self._save(result, region_code))

    def for_region(self, outcome: ScanOutcome, region_code: str) -> ScanOutcome:
        """Show an earlier scan for another region, without classifying or saving it again.

        One photo is one scan, so the dashboard keeps it under the region it was first saved for.

        Args:
            outcome: the result of an earlier run().
            region_code: the region now selected, e.g. "DO".
        """
        if outcome.explanation is None or outcome.explanation.region_code == region_code:
            return outcome
        return replace(outcome, explanation=self.services.coach.explain_result(outcome.result, region_code))

    def _save(self, result: ClassificationResult, region_code: str) -> int | None:
        """Store the scan. A database problem must not hide the answer from the user."""
        try:
            return self.services.dal.save_result(result.material, result.category, result.confidence, region_code)
        except Exception:
            logger.exception("Could not save the scan")
            return None
