"""Settings. Paths and limits are read from the environment, never hard-coded."""
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL_PATH = "models/mobilenet_waste.pt"
DEFAULT_LABELS_PATH = "models/labels.json"

# The folder that contains src/ and models/. Default paths are relative to it, so the
# model is found no matter from which folder the app is started.
PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_MAX_IMAGE_MB = 10.0


@dataclass(frozen=True)
class ClassificationConfig:
    """All settings of the classification engine in one place."""

    model_path: Path
    labels_path: Path
    confidence_threshold: float
    max_image_mb: float

    @classmethod
    def from_env(cls) -> "ClassificationConfig":
        """Build the settings from environment variables, using defaults for missing ones.

        Raises:
            ValueError: if a number is malformed or out of range.
        """
        threshold = _read_float("CONFIDENCE_THRESHOLD", DEFAULT_CONFIDENCE_THRESHOLD)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"CONFIDENCE_THRESHOLD must be between 0 and 1, got {threshold}.")

        max_mb = _read_float("MAX_IMAGE_MB", DEFAULT_MAX_IMAGE_MB)
        if max_mb <= 0:
            raise ValueError(f"MAX_IMAGE_MB must be greater than 0, got {max_mb}.")

        return cls(
            model_path=Path(os.environ.get("MODEL_PATH", PROJECT_DIR / DEFAULT_MODEL_PATH)),
            labels_path=Path(os.environ.get("LABELS_PATH", PROJECT_DIR / DEFAULT_LABELS_PATH)),
            confidence_threshold=threshold,
            max_image_mb=max_mb,
        )


def _read_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}.") from None
