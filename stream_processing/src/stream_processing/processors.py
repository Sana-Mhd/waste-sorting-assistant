"""The stream processors. All have the same API, so they can be combined with |.

    pipeline = ConfidenceFilter(0.6) | MaterialMapper() | RouteAssigner()
    for item in pipeline.process(stream):
        ...
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import replace

from .events import BoundingBox, SorterEvent

DEFAULT_THRESHOLD = 0.6
OTHER = "Other"

# An item has a material if it shows all of these visual tags.
MATERIAL_RULES = (
    ({"bottle", "transparent"}, "PET"),
    ({"bottle", "opaque"}, "HDPE"),
    ({"can", "metallic"}, "Aluminum"),
)

# Which conveyor lane takes which material. RJ is the reject lane.
LANES = {"PET": "A1", "HDPE": "A2", "Aluminum": "B1", OTHER: "RJ"}

SMALL_AREA = 5_000      # pixels; below this an item counts as small
LARGE_AREA = 20_000     # pixels; from this size on an item counts as large


class StreamProcessor(ABC):
    """One step of a pipeline: it takes a stream of events and gives a new one."""

    @abstractmethod
    def process(self, stream: Iterable[SorterEvent]) -> Iterator[SorterEvent]:
        """Go through the stream and give back the resulting events one by one."""

    def __or__(self, other: "StreamProcessor") -> "Pipeline":
        """`first | second` builds a pipeline that runs first, then second."""
        if not isinstance(other, StreamProcessor):
            return NotImplemented
        return Pipeline(self, other)


class ConfidenceFilter(StreamProcessor):
    """Removes the predictions the image recognition is not sure about."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"The threshold must be between 0 and 1, got {threshold}.")
        self.threshold = threshold

    def process(self, stream: Iterable[SorterEvent]) -> Iterator[SorterEvent]:
        for event in stream:
            if event.confidence >= self.threshold:
                yield event


class MaterialMapper(StreamProcessor):
    """Turns the visual tags into a material, e.g. PET, HDPE or Aluminum."""

    def process(self, stream: Iterable[SorterEvent]) -> Iterator[SorterEvent]:
        for event in stream:
            yield replace(event, material=self._material(event.tags))

    @staticmethod
    def _material(tags: tuple[str, ...]) -> str:
        for needed_tags, material in MATERIAL_RULES:
            if needed_tags.issubset(tags):
                return material
        return OTHER


class RouteAssigner(StreamProcessor):
    """Turns the material and the box size into a routing code, e.g. "A1-L"."""

    def process(self, stream: Iterable[SorterEvent]) -> Iterator[SorterEvent]:
        for event in stream:
            if event.material is None:
                raise ValueError("RouteAssigner needs a material, so run MaterialMapper first.")
            code = f"{LANES[event.material]}-{self._size(event.box)}"
            yield replace(event, routing_code=code)

    @staticmethod
    def _size(box: BoundingBox) -> str:
        if box.area < SMALL_AREA:
            return "S"
        return "L" if box.area >= LARGE_AREA else "M"


class Pipeline(StreamProcessor):
    """Several processors that run one after the other. It is also a processor itself."""

    def __init__(self, *steps: StreamProcessor) -> None:
        if not steps:
            raise ValueError("A pipeline needs at least one step.")
        self.steps = steps

    def process(self, stream: Iterable[SorterEvent]) -> Iterator[SorterEvent]:
        for step in self.steps:
            stream = step.process(stream)
        yield from stream
