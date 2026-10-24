"""Tests for Subsystem 1 (Classification Engine). They run without trained weights."""
import dataclasses
import io
import json
import logging
import os
import time

import pytest
import torch
from PIL import Image
from torch import nn
from torchvision import models

from classification import (
    MATERIAL_TO_CATEGORY,
    ClassificationConfig,
    ClassificationEngine,
    DummyClassifier,
    ImagePreprocessor,
    InvalidImageError,
    MobileNetClassifier,
    ModelNotFoundError,
    to_category,
)
from classification.config import PROJECT_DIR
from data_rules import CATEGORIES


def make_image(size=(320, 240), mode="RGB", noise=False) -> Image.Image:
    if noise:
        return Image.frombytes(mode, size, os.urandom(size[0] * size[1] * len(mode)))
    return Image.new(mode, size, color="green" if mode == "RGB" else 128)


def image_bytes(fmt="PNG", **kwargs) -> bytes:
    buffer = io.BytesIO()
    make_image(**kwargs).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def png_path(tmp_path):
    path = tmp_path / "bottle.png"
    make_image().save(path)
    return path


class PassThroughPreprocessor:
    """Stand-in for the real preprocessor: hands the input straight to the classifier."""

    def process(self, image):
        return image


def make_engine(material: str = "plastic", confidence: float = 0.9) -> ClassificationEngine:
    return ClassificationEngine(
        classifier=DummyClassifier(material, confidence),
        preprocessor=PassThroughPreprocessor(),
        confidence_threshold=0.6,
    )


# --- mapping -----------------------------------------------------------------

def test_every_material_maps_to_a_data_rules_category():
    """Contract check: data_rules must accept every category we can return."""
    for material, category in MATERIAL_TO_CATEGORY.items():
        assert category in CATEGORIES, f"{material} -> {category} is not in data_rules.CATEGORIES"


def test_mapping_has_the_seven_materials():
    assert set(MATERIAL_TO_CATEGORY) == {
        "paper", "cardboard", "plastic", "metal", "glass", "organic", "trash",
    }


@pytest.mark.parametrize("material, category", [
    ("glass", "recyclable"), ("organic", "compostable"), ("trash", "landfill"),
])
def test_to_category(material, category):
    assert to_category(material) == category


def test_to_category_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown material"):
        to_category("unknown")


# --- engine with the dummy classifier ----------------------------------------

def test_low_confidence_is_not_confident():
    result = make_engine("plastic", 0.3).classify(b"fake image")
    assert result.confidence == pytest.approx(0.3)
    assert result.is_confident is False


def test_high_confidence_is_confident_and_category_correct():
    result = make_engine("organic", 0.9).classify(b"fake image")
    assert result.material == "organic"
    assert result.category == "compostable"
    assert result.is_confident is True


def test_confidence_equal_to_threshold_counts_as_confident():
    assert make_engine("metal", 0.6).classify(b"x").is_confident is True


def test_top3_is_sorted_and_valid():
    top3 = make_engine("glass", 0.7).classify(b"x").top3
    assert 1 <= len(top3) <= 3
    probabilities = [p for _, p in top3]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in probabilities)
    assert top3[0][0] == "glass"


def test_result_is_frozen():
    result = make_engine().classify(b"x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.material = "glass"


def test_engine_rejects_bad_threshold():
    with pytest.raises(ValueError):
        ClassificationEngine(DummyClassifier(), PassThroughPreprocessor(), confidence_threshold=1.5)


# --- dummy classifier ----------------------------------------------------------

def test_dummy_probabilities_sum_to_one():
    predictions = DummyClassifier("paper", 0.8).predict(None)
    assert len(predictions) == len(MATERIAL_TO_CATEGORY)
    assert sum(p for _, p in predictions) == pytest.approx(1.0)


def test_dummy_rejects_unknown_material():
    with pytest.raises(ValueError):
        DummyClassifier("banana", 0.9)


def test_dummy_rejects_bad_confidence():
    with pytest.raises(ValueError):
        DummyClassifier("paper", 1.2)


# --- config ------------------------------------------------------------------

def test_config_defaults(monkeypatch):
    for name in ("MODEL_PATH", "LABELS_PATH", "CONFIDENCE_THRESHOLD", "MAX_IMAGE_MB"):
        monkeypatch.delenv(name, raising=False)
    config = ClassificationConfig.from_env()
    assert config.model_path == PROJECT_DIR / "models" / "mobilenet_waste.pt"
    assert config.labels_path == PROJECT_DIR / "models" / "labels.json"
    assert config.confidence_threshold == 0.6
    assert config.max_image_mb == 10


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.75")
    monkeypatch.setenv("MODEL_PATH", "/tmp/model.pt")
    config = ClassificationConfig.from_env()
    assert config.confidence_threshold == 0.75
    assert str(config.model_path) == "/tmp/model.pt"


@pytest.mark.parametrize("value", ["abc", "1.5", "-0.1"])
def test_config_rejects_bad_threshold(monkeypatch, value):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", value)
    with pytest.raises(ValueError, match="CONFIDENCE_THRESHOLD"):
        ClassificationConfig.from_env()


# --- preprocessing -----------------------------------------------------------

def test_preprocessing_path_gives_model_shape(png_path):
    tensor = ImagePreprocessor().process(png_path)
    assert tuple(tensor.shape) == (1, 3, 224, 224)


def test_preprocessing_accepts_str_path(png_path):
    assert tuple(ImagePreprocessor().process(str(png_path)).shape) == (1, 3, 224, 224)


def test_preprocessing_bytes_gives_model_shape():
    tensor = ImagePreprocessor().process(image_bytes("JPEG"))
    assert tuple(tensor.shape) == (1, 3, 224, 224)


def test_path_and_bytes_give_the_same_tensor(png_path):
    preprocessor = ImagePreprocessor()
    from_path = preprocessor.process(png_path)
    from_bytes = preprocessor.process(png_path.read_bytes())
    assert from_path.equal(from_bytes)


@pytest.mark.parametrize("mode", ["L", "RGBA"])
def test_grayscale_and_transparent_images_become_rgb(mode):
    tensor = ImagePreprocessor().process(image_bytes("PNG", mode=mode))
    assert tuple(tensor.shape) == (1, 3, 224, 224)


def test_exif_orientation_is_applied():
    """A landscape JPEG tagged 'rotate 90 degrees' must come out as portrait."""
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation tag: rotate 90 degrees clockwise
    buffer = io.BytesIO()
    make_image(size=(100, 50)).save(buffer, format="JPEG", exif=exif)
    picture = ImagePreprocessor().load_image(buffer.getvalue())
    assert picture.size == (50, 100)


def test_text_file_renamed_to_jpg_raises(tmp_path):
    fake = tmp_path / "photo.jpg"
    fake.write_text("this is not an image")
    with pytest.raises(InvalidImageError, match="not a readable image"):
        ImagePreprocessor().process(fake)


def test_unsupported_format_raises():
    with pytest.raises(InvalidImageError, match="GIF"):
        ImagePreprocessor().process(image_bytes("GIF"))


def test_oversized_file_raises(tmp_path):
    big = tmp_path / "big.png"
    make_image(size=(200, 200), noise=True).save(big)   # ~120 KB, does not compress
    with pytest.raises(InvalidImageError, match="too large"):
        ImagePreprocessor(max_image_mb=0.05).process(big)


def test_oversized_bytes_raise():
    data = image_bytes("PNG", size=(200, 200), noise=True)
    with pytest.raises(InvalidImageError, match="too large"):
        ImagePreprocessor(max_image_mb=0.05).process(data)


def test_missing_file_raises(tmp_path):
    with pytest.raises(InvalidImageError, match="not found"):
        ImagePreprocessor().process(tmp_path / "nope.jpg")


def test_empty_bytes_raise():
    with pytest.raises(InvalidImageError, match="empty"):
        ImagePreprocessor().process(b"")


def test_wrong_input_type_raises_type_error():
    with pytest.raises(TypeError):
        ImagePreprocessor().process(42)


def test_engine_with_real_preprocessor_and_dummy(png_path):
    engine = ClassificationEngine(DummyClassifier("cardboard", 0.85), ImagePreprocessor())
    result = engine.classify(png_path.read_bytes())
    assert result.material == "cardboard"
    assert result.category == "recyclable"
    assert result.is_confident is True


def test_engine_rejects_invalid_upload():
    engine = ClassificationEngine(DummyClassifier(), ImagePreprocessor())
    with pytest.raises(InvalidImageError):
        engine.classify(b"definitely not a photo")


# --- MobileNet classifier and from_config --------------------------------------

LABELS = ["cardboard", "glass", "metal", "organic", "paper", "plastic", "trash"]  # ImageFolder order


@pytest.fixture(scope="module")
def untrained_model_files(tmp_path_factory):
    """Random (untrained) weights with the right architecture, so no download or training is needed."""
    folder = tmp_path_factory.mktemp("model")
    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(1280, len(LABELS))
    torch.save(model.state_dict(), folder / "mobilenet_waste.pt")
    (folder / "labels.json").write_text(json.dumps(LABELS))
    return folder / "mobilenet_waste.pt", folder / "labels.json"


def use_model_files(monkeypatch, model_path, labels_path):
    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("LABELS_PATH", str(labels_path))


def test_missing_weights_raise_model_not_found(tmp_path):
    with pytest.raises(ModelNotFoundError, match="not found"):
        MobileNetClassifier(tmp_path / "missing.pt", tmp_path / "labels.json")


def test_missing_labels_raise_model_not_found(untrained_model_files, tmp_path):
    model_path, _ = untrained_model_files
    with pytest.raises(ModelNotFoundError, match="Labels file"):
        MobileNetClassifier(model_path, tmp_path / "missing.json")


def test_mobilenet_predicts_all_materials_sorted(untrained_model_files):
    classifier = MobileNetClassifier(*untrained_model_files)
    predictions = classifier.predict(torch.zeros(1, 3, 224, 224))
    assert sorted(label for label, _ in predictions) == sorted(LABELS)
    probabilities = [p for _, p in predictions]
    assert probabilities == sorted(probabilities, reverse=True)
    assert sum(probabilities) == pytest.approx(1.0, abs=1e-5)


def test_labels_that_do_not_fit_the_weights_raise(untrained_model_files, tmp_path):
    model_path, _ = untrained_model_files
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps(["paper", "plastic", "glass"]))
    with pytest.raises(ValueError, match="do not fit"):
        MobileNetClassifier(model_path, labels)


def test_unknown_label_raises(untrained_model_files, tmp_path):
    model_path, _ = untrained_model_files
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps(LABELS[:-1] + ["banana"]))
    with pytest.raises(ValueError, match="banana"):
        MobileNetClassifier(model_path, labels)


def test_from_config_falls_back_to_dummy_without_weights(monkeypatch, tmp_path, caplog):
    use_model_files(monkeypatch, tmp_path / "missing.pt", tmp_path / "labels.json")
    with caplog.at_level(logging.WARNING, logger="classification"):
        engine = ClassificationEngine.from_config()
    assert isinstance(engine.classifier, DummyClassifier)
    assert engine.is_demo_mode is True
    assert "DummyClassifier" in caplog.text


def test_from_config_falls_back_on_broken_weights(monkeypatch, tmp_path):
    broken = tmp_path / "broken.pt"
    broken.write_bytes(b"not a torch file")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps(LABELS))
    use_model_files(monkeypatch, broken, labels)
    assert ClassificationEngine.from_config().is_demo_mode is True


def test_from_config_uses_mobilenet_when_weights_exist(monkeypatch, untrained_model_files, png_path):
    use_model_files(monkeypatch, *untrained_model_files)
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.7")
    engine = ClassificationEngine.from_config()
    assert isinstance(engine.classifier, MobileNetClassifier)
    assert engine.is_demo_mode is False
    assert engine.confidence_threshold == 0.7

    result = engine.classify(png_path)
    assert result.material in LABELS
    assert result.category == MATERIAL_TO_CATEGORY[result.material]
    assert len(result.top3) == 3


TRAINED = ClassificationConfig.from_env()


@pytest.mark.skipif(not TRAINED.model_path.is_file(), reason="trained weights not available")
def test_one_inference_under_one_second_on_cpu(png_path):
    engine = ClassificationEngine.from_config()
    assert engine.is_demo_mode is False
    engine.classify(png_path)  # warm-up: the first call allocates memory
    start = time.perf_counter()
    engine.classify(png_path)
    assert time.perf_counter() - start < 1.0


def test_default_model_path_does_not_depend_on_start_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("MODEL_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert ClassificationConfig.from_env().model_path.is_absolute()
