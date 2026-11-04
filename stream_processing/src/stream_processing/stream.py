"""The source of the events: an iterator over the messages of the optical sorter."""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable, Iterator

from .events import SorterEvent

logger = logging.getLogger(__name__)

# What the simulated camera can see, with the material it stands for in brackets.
SIMULATED_TAGS = (
    ("bottle", "transparent"),      # PET
    ("bottle", "opaque"),           # HDPE
    ("can", "metallic"),            # Aluminum
    ("box", "brown"),               # no rule, so it goes to the reject lane
)


class SorterStream:
    """Gives one SorterEvent at a time from a source of raw messages.

    This is an iterator: a for loop calls __iter__ once and then __next__ for
    every event. A broken message is logged and skipped, so one bad reading
    does not stop the conveyor belt.
    """

    def __init__(self, payloads: Iterable[dict]) -> None:
        """
        Args:
            payloads: the raw messages, e.g. a list or a live generator.
        """
        self._payloads = iter(payloads)
        self.skipped = 0

    def __iter__(self) -> "SorterStream":
        return self

    def __next__(self) -> SorterEvent:
        """Return the next valid event. Raises StopIteration when the source is finished."""
        while True:
            payload = next(self._payloads)
            try:
                return SorterEvent.from_payload(payload)
            except (KeyError, TypeError, ValueError) as error:
                self.skipped += 1
                logger.warning("Skipped a broken message: %r", error)


def simulate_payloads(count: int, seed: int = 42, delay: float = 0.0) -> Iterator[dict]:
    """A generator that acts like a real sorter: it creates one message at a time.

    Args:
        count: how many messages to create.
        seed: the same seed always gives the same messages.
        delay: seconds to wait between messages, to look like a live belt.
    """
    rng = random.Random(seed)
    for number in range(1, count + 1):
        if delay:
            time.sleep(delay)
        yield {
            "item_id": f"item-{number:03d}",
            "confidence": round(rng.uniform(0.3, 1.0), 2),
            "box": {
                "x": rng.randint(0, 600),
                "y": rng.randint(0, 400),
                "width": rng.randint(20, 200),
                "height": rng.randint(20, 200),
            },
            "tags": list(rng.choice(SIMULATED_TAGS)),
        }
