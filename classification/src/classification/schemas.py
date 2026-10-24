"""Plain data objects that cross the subsystem boundary.

The web interface and the AI coach receive a ClassificationResult, never a
torch tensor, so nobody outside this package needs to know how the model works.
"""
from dataclasses import dataclass
from pathlib import Path

# What classify() accepts: a file path, or the raw bytes of a Streamlit upload.
ImageInput = str | Path | bytes


@dataclass(frozen=True)
class ClassificationResult:
    """The answer of the classification engine for one photo."""

    material: str                   # e.g. "plastic" (one of the 7 materials)
    category: str                   # "recyclable" | "compostable" | "landfill"
    confidence: float               # probability of the top material, 0..1
    is_confident: bool              # True if confidence >= CONFIDENCE_THRESHOLD
    top3: list[tuple[str, float]]   # best three (material, probability), highest first
