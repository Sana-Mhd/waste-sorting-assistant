"""Evaluate the trained model on the test split (and optionally on your own photos).

Every image goes through the same ImagePreprocessor + MobileNetClassifier as in the app,
so the numbers show what users will actually get. Prints and saves to reports/:
  - overall and per-class accuracy, sklearn classification report
  - confusion matrix as PNG
  - threshold table: for each confidence threshold, how many predictions are kept
    (coverage) and how accurate the kept ones are

Usage:
    python training/evaluate.py                               # data/test
    python training/evaluate.py --folder my_photos            # also my_photos/<class>/*.jpg
"""
import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window needed, we only save PNG files
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classification import ImagePreprocessor, InvalidImageError, MobileNetClassifier  # noqa: E402

logger = logging.getLogger("evaluate")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
THRESHOLDS = np.round(np.arange(0.40, 0.901, 0.05), 2)


@dataclass
class Predictions:
    """True labels, predicted labels and confidences of one evaluated folder."""

    true: list[str]
    predicted: list[str]
    confidence: list[float]


def predict_folder(folder: Path, classifier: MobileNetClassifier, preprocessor: ImagePreprocessor) -> Predictions:
    """Classify every image in folder/<class>/; the subfolder name is the true label."""
    result = Predictions([], [], [])
    for class_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        if class_dir.name not in classifier.labels:
            logger.warning("Skipping folder %s: not a class of the model", class_dir.name)
            continue
        for image_path in sorted(class_dir.iterdir()):
            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                tensor = preprocessor.process(image_path)
            except InvalidImageError as error:
                logger.warning("Skipping %s: %s", image_path, error)
                continue
            material, confidence = classifier.predict(tensor)[0]
            result.true.append(class_dir.name)
            result.predicted.append(material)
            result.confidence.append(confidence)
    return result


def build_report(name: str, preds: Predictions, labels: list[str]) -> str:
    """Accuracy, per-class accuracy, classification report and threshold table as text."""
    true, predicted = np.array(preds.true), np.array(preds.predicted)
    confidence = np.array(preds.confidence)
    correct = true == predicted

    lines = [f"=== {name}: {len(true)} images ===", f"Overall accuracy: {correct.mean():.3f}", "", "Per-class accuracy:"]
    for label in labels:
        mask = true == label
        if mask.any():
            lines.append(f"  {label:<10} {correct[mask].mean():.3f}  (n={mask.sum()})")
        else:
            lines.append(f"  {label:<10}   -    (n=0)")

    lines += ["", classification_report(true, predicted, labels=labels, zero_division=0), "Threshold table:",
              "  threshold  coverage  accuracy_on_kept"]
    for threshold in THRESHOLDS:
        kept = confidence >= threshold
        accuracy = f"{correct[kept].mean():.3f}" if kept.any() else "  -  "
        lines.append(f"  {threshold:9.2f}  {kept.mean():7.1%}  {accuracy:>16}")
    return "\n".join(lines)


def save_confusion_matrix(name: str, preds: Predictions, labels: list[str], reports_dir: Path) -> Path:
    """Save the confusion matrix as reports/confusion_matrix_<name>.png."""
    matrix = confusion_matrix(preds.true, preds.predicted, labels=labels)
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay(matrix, display_labels=labels).plot(ax=ax, cmap="Blues", colorbar=False, xticks_rotation=45)
    ax.set_title(f"Confusion matrix: {name}")
    fig.tight_layout()
    path = reports_dir / f"confusion_matrix_{name}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def evaluate(name: str, folder: Path, classifier: MobileNetClassifier, preprocessor: ImagePreprocessor,
             reports_dir: Path) -> None:
    """Evaluate one folder, print the report and save it plus the confusion matrix."""
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")
    preds = predict_folder(folder, classifier, preprocessor)
    if not preds.true:
        raise SystemExit(f"No images found in {folder}/<class>/")

    labels = list(classifier.labels)
    report = build_report(name, preds, labels)
    print(report)
    (reports_dir / f"report_{name}.txt").write_text(report + "\n")
    png = save_confusion_matrix(name, preds, labels, reports_dir)
    logger.info("Saved %s and %s", reports_dir / f"report_{name}.txt", png)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="uses <data-dir>/test")
    parser.add_argument("--model", type=Path, default=Path("models/mobilenet_waste.pt"))
    parser.add_argument("--labels", type=Path, default=Path("models/labels.json"))
    parser.add_argument("--folder", type=Path, help="extra folder of real-world photos, as <folder>/<class>/*.jpg")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    classifier = MobileNetClassifier(args.model, args.labels)
    preprocessor = ImagePreprocessor(max_image_mb=50)  # evaluation photos may be large phone pictures

    evaluate("test", args.data_dir / "test", classifier, preprocessor, args.reports_dir)
    if args.folder:
        print()
        evaluate("real_world", args.folder, classifier, preprocessor, args.reports_dir)


if __name__ == "__main__":
    main()
