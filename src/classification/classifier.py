"""Subsystem 1 - Classification Engine.

OWNER: <name>

Contract with the rest of the team
----------------------------------
    classify(image_path: str) -> Classification

Everything else in this module is private to subsystem 1.  As long as
`classify` keeps returning a `Classification`, the other three subsystems do
not care how it works.

Right now it returns a fixed answer so that the whole application already
runs end to end.  Replace the body of `classify` with the real model.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# The only three categories the system knows about.
CATEGORIES = ("recyclable", "compostable", "landfill")

# Below this confidence the application asks the user for a better photo
# instead of showing a possibly wrong answer.
MIN_CONFIDENCE = 0.60


@dataclass
class Classification:
    """What subsystem 1 hands back for one photo."""

    item: str           # what was recognised, e.g. "plastic bottle"
    category: str       # one of CATEGORIES
    confidence: float   # 0.0 - 1.0

    @property
    def is_confident(self) -> bool:
        return self.confidence >= MIN_CONFIDENCE


def classify(image_path: str) -> Classification:
    """Classify the waste item on the given photo.

    TODO (subsystem 1): load the trained model and run a real prediction.
    """
    # --- temporary stand-in so the rest of the team can work ---------------
    sample = [
        ("plastic bottle", "recyclable", 0.93),
        ("banana peel", "compostable", 0.88),
        ("ceramic cup", "landfill", 0.71),
        ("unknown object", "landfill", 0.41),
    ]
    item, category, confidence = random.choice(sample)
    return Classification(item=item, category=category, confidence=confidence)
