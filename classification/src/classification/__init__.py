"""Subsystem 1: Classification Engine.

Public API for the other subsystems:

    from classification import ClassificationEngine

    engine = ClassificationEngine.from_config()     # real model, or a dummy if no weights yet
    result = engine.classify("photo.jpg")           # path or raw bytes
    result.material, result.category, result.confidence, result.is_confident, result.top3
"""
from .classifiers import BaseClassifier, DummyClassifier, MobileNetClassifier
from .config import ClassificationConfig
from .engine import ClassificationEngine
from .exceptions import InvalidImageError, ModelNotFoundError
from .mapping import MATERIAL_TO_CATEGORY, MATERIALS, to_category
from .preprocessing import ImagePreprocessor
from .schemas import ClassificationResult

__all__ = [
    "MATERIALS",
    "MATERIAL_TO_CATEGORY",
    "BaseClassifier",
    "ClassificationConfig",
    "ClassificationEngine",
    "ClassificationResult",
    "DummyClassifier",
    "ImagePreprocessor",
    "InvalidImageError",
    "MobileNetClassifier",
    "ModelNotFoundError",
    "to_category",
]
