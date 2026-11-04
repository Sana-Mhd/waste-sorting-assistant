"""Getters and setters of the classification classes (Hometask 1)."""
import pytest

from classification import ClassificationEngine, DummyClassifier, ImagePreprocessor


def test_engine_getters_and_setters():
    engine = ClassificationEngine(DummyClassifier(), ImagePreprocessor())
    other_classifier, other_preprocessor = DummyClassifier("glass"), ImagePreprocessor(5)

    engine.classifier = other_classifier
    engine.preprocessor = other_preprocessor
    engine.confidence_threshold = 0.8

    assert engine.classifier is other_classifier
    assert engine.preprocessor is other_preprocessor
    assert engine.confidence_threshold == 0.8


def test_engine_refuses_a_threshold_out_of_range():
    engine = ClassificationEngine(DummyClassifier(), ImagePreprocessor())
    with pytest.raises(ValueError):
        engine.confidence_threshold = 1.5


def test_dummy_classifier_getters_and_setters():
    classifier = DummyClassifier()

    classifier.material = "glass"
    classifier.confidence = 0.7
    classifier.labels = ["glass", "metal"]

    assert classifier.material == "glass"
    assert classifier.confidence == 0.7
    assert classifier.labels == ("glass", "metal")


def test_dummy_classifier_refuses_bad_values():
    classifier = DummyClassifier()
    with pytest.raises(ValueError):
        classifier.material = ""
    with pytest.raises(ValueError):
        classifier.confidence = 2.0


def test_preprocessor_getters_and_setters():
    preprocessor = ImagePreprocessor()

    preprocessor.max_image_mb = 5
    assert preprocessor.max_image_mb == 5

    steps = preprocessor.transform
    preprocessor.transform = steps
    assert preprocessor.transform is steps

    with pytest.raises(ValueError):
        preprocessor.max_image_mb = 0
