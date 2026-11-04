"""Hometask 2: a real-time stream processing framework for a conveyor belt optical sorter."""
from .events import BoundingBox, SorterEvent
from .processors import ConfidenceFilter, MaterialMapper, Pipeline, RouteAssigner, StreamProcessor
from .stream import SorterStream, simulate_payloads

__all__ = [
    "BoundingBox",
    "ConfidenceFilter",
    "MaterialMapper",
    "Pipeline",
    "RouteAssigner",
    "SorterEvent",
    "SorterStream",
    "StreamProcessor",
    "simulate_payloads",
]
