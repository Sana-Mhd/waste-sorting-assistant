"""The ClassificationEngine: the only class the other subsystems need.

It is built by composition: it holds a preprocessor (photo -> tensor) and a
classifier (tensor -> probabilities) and turns their output into a ClassificationResult.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from .classifiers import BaseClassifier, DummyClassifier, MobileNetClassifier
from .config import DEFAULT_CONFIDENCE_THRESHOLD, ClassificationConfig
from .exceptions import ModelNotFoundError
from .mapping import to_category
from .preprocessing import ImagePreprocessor
from .schemas import ClassificationResult, ImageInput

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)


class Preprocessor(Protocol):
    """Anything that turns a photo (path or bytes) into a model input tensor."""

    def process(self, image: ImageInput) -> torch.Tensor: ...


class ClassificationEngine:
    """Classify a photo of a waste item into a material and a waste category."""

    def __init__(
        self,
        classifier: BaseClassifier,
        preprocessor: Preprocessor,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(f"Confidence threshold must be between 0 and 1, got {confidence_threshold}.")
        self.classifier = classifier
        self.preprocessor = preprocessor
        self.confidence_threshold = confidence_threshold

    @classmethod
    def from_config(cls, config: ClassificationConfig | None = None) -> "ClassificationEngine":
        """Build the engine from the environment settings (MODEL_PATH, LABELS_PATH, ...).

        Uses the trained MobileNetV2 if its files exist. Otherwise it logs a warning and
        falls back to a DummyClassifier, so the app keeps running before training is done.
        """
        config = config or ClassificationConfig.from_env()
        preprocessor = ImagePreprocessor(max_image_mb=config.max_image_mb)
        try:
            classifier: BaseClassifier = MobileNetClassifier(config.model_path, config.labels_path)
        except ModelNotFoundError as error:
            logger.warning("%s Falling back to DummyClassifier (demo mode).", error)
            classifier = DummyClassifier()
        except Exception:
            logger.exception("Could not load the model. Falling back to DummyClassifier (demo mode).")
            classifier = DummyClassifier()
        return cls(classifier, preprocessor, config.confidence_threshold)

    @property
    def is_demo_mode(self) -> bool:
        """True if the engine runs with the DummyClassifier instead of a trained model."""
        return isinstance(self.classifier, DummyClassifier)

    def classify(self, image: ImageInput) -> ClassificationResult:
        """Classify one photo.

        Args:
            image: file path (str or Path) or raw bytes, e.g. from a Streamlit upload.

        Raises:
            InvalidImageError: if the photo cannot be read or is not allowed.
        """
        tensor = self.preprocessor.process(image)
        predictions = self.classifier.predict(tensor)
        if not predictions:
            raise RuntimeError("The classifier returned no predictions.")

        material, confidence = predictions[0]
        result = ClassificationResult(
            material=material,
            category=to_category(material),
            confidence=confidence,
            is_confident=confidence >= self.confidence_threshold,
            top3=predictions[:3],
        )
        logger.info("Classified as %s (%.2f, confident=%s)", material, confidence, result.is_confident)
        return result
