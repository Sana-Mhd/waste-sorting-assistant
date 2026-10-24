"""Classifiers: turn a preprocessed image tensor into material probabilities.

BaseClassifier is the abstract interface. The engine only talks to this interface,
so a real model and a fake one can be swapped without changing any other code.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import torch
from torch import nn
from torchvision import models

from .exceptions import ModelNotFoundError
from .mapping import MATERIAL_TO_CATEGORY, MATERIALS

logger = logging.getLogger(__name__)


class BaseClassifier(ABC):
    """Interface for every classifier used by the ClassificationEngine."""

    @abstractmethod
    def predict(self, tensor: torch.Tensor) -> list[tuple[str, float]]:
        """Return every material with its probability, sorted from highest to lowest.

        Args:
            tensor: preprocessed image of shape (1, 3, 224, 224).
        """


class DummyClassifier(BaseClassifier):
    """Fake classifier that always gives the same answer. Needs no model weights.

    Useful for teammates (the app runs before the model is trained) and for tests.
    The chosen material gets `confidence`; the rest is shared equally by the others.
    Pick a confidence above 1/len(labels) so the chosen material stays on top.
    """

    def __init__(
        self,
        material: str = "plastic",
        confidence: float = 0.9,
        labels: tuple[str, ...] | list[str] = MATERIALS,
    ) -> None:
        if material not in labels:
            raise ValueError(f"Unknown material {material!r}. Known materials: {', '.join(labels)}.")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {confidence}.")
        self.material = material
        self.confidence = confidence
        self.labels = tuple(labels)

    def predict(self, tensor: torch.Tensor) -> list[tuple[str, float]]:
        """Return the fixed answer as a full, sorted probability list (the tensor is ignored)."""
        others = [label for label in self.labels if label != self.material]
        share = (1.0 - self.confidence) / len(others) if others else 0.0
        predictions = [(self.material, self.confidence)] + [(label, share) for label in others]
        return sorted(predictions, key=lambda pair: pair[1], reverse=True)


class MobileNetClassifier(BaseClassifier):
    """MobileNetV2 fine-tuned on waste photos (see training/train.py). Runs on the CPU."""

    def __init__(self, model_path: str | Path, labels_path: str | Path) -> None:
        """Load the labels and the trained weights.

        Raises:
            ModelNotFoundError: if the weights file or the labels file does not exist.
            ValueError: if the labels are unknown or do not match the weights.
        """
        model_path, labels_path = Path(model_path), Path(labels_path)
        if not model_path.is_file():
            raise ModelNotFoundError(f"Model weights not found at {model_path}. Train the model first (training/train.py).")

        self.labels = load_labels(labels_path)
        self.model = models.mobilenet_v2(weights=None)
        self.model.classifier[1] = nn.Linear(1280, len(self.labels))

        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
        try:
            self.model.load_state_dict(state_dict)
        except RuntimeError as error:
            raise ValueError(
                f"The weights in {model_path} do not fit {len(self.labels)} labels from {labels_path}. "
                "Use the labels.json saved together with this model."
            ) from error
        self.model.eval()
        logger.info("Loaded MobileNetV2 from %s with labels %s", model_path, self.labels)

    def predict(self, tensor: torch.Tensor) -> list[tuple[str, float]]:
        """Run the model and return every material with its softmax probability, highest first."""
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0].tolist()
        return sorted(zip(self.labels, probabilities), key=lambda pair: pair[1], reverse=True)


def load_labels(labels_path: str | Path) -> tuple[str, ...]:
    """Read the class names in model output order from labels.json.

    Raises:
        ModelNotFoundError: if the file does not exist.
        ValueError: if the file is not a JSON list of known material names.
    """
    labels_path = Path(labels_path)
    if not labels_path.is_file():
        raise ModelNotFoundError(f"Labels file not found at {labels_path}. It is saved by training/train.py.")
    try:
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{labels_path} is not valid JSON.") from error

    if not isinstance(labels, list) or not labels or not all(isinstance(label, str) for label in labels):
        raise ValueError(f"{labels_path} must contain a list of material names.")
    unknown = [label for label in labels if label not in MATERIAL_TO_CATEGORY]
    if unknown:
        raise ValueError(f"{labels_path} contains unknown materials: {', '.join(unknown)}.")
    return tuple(labels)
