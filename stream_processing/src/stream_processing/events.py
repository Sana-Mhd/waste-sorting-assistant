"""The data that moves through the stream: one detected item on the conveyor belt."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """Where the optical sorter saw the item, in pixels."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"A box needs a positive size, got {self.width} x {self.height}.")

    @property
    def area(self) -> int:
        """The size of the item in the picture, in pixels."""
        return self.width * self.height


@dataclass(frozen=True)
class SorterEvent:
    """One item seen by the optical sorter. Processors add the last two fields."""

    item_id: str
    confidence: float           # how sure the image recognition is, from 0 to 1
    box: BoundingBox
    tags: tuple[str, ...]       # what the camera saw, e.g. ("bottle", "transparent")
    material: str | None = None         # set by MaterialMapper
    routing_code: str | None = None     # set by RouteAssigner

    @classmethod
    def from_payload(cls, payload: dict) -> "SorterEvent":
        """Build an event from one raw message of the sorter.

        Raises:
            KeyError, TypeError, ValueError: if the message is incomplete or has bad values.
        """
        return cls(
            item_id=str(payload["item_id"]),
            confidence=float(payload["confidence"]),
            box=BoundingBox(**payload["box"]),
            tags=tuple(payload["tags"]),
        )
