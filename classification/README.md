# Subsystem 1: Classification Engine

Computer vision part of the waste sorting assistant. It takes a photo of a household item,
predicts the material with a fine-tuned MobileNetV2, maps it to a waste category and says
whether the prediction is confident enough to show.

## Setup

```bash
cd classification
pip install -r requirements.txt
python -m pytest            # also runs without trained weights (then the speed test is skipped)
```

Settings come from environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MODEL_PATH` | `models/mobilenet_waste.pt` in this folder | trained weights (state_dict) |
| `LABELS_PATH` | `models/labels.json` in this folder | class names in model output order |
| `CONFIDENCE_THRESHOLD` | `0.6` | below this, `is_confident` is `False` |
| `MAX_IMAGE_MB` | `10` | larger uploads are rejected |

### Docker: install CPU-only torch

The normal `torch` wheel includes CUDA and is several GB. The app only runs on the CPU, so in the
Dockerfile install torch from the CPU index **before** the rest of the requirements:

```dockerfile
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt
```

Copy `models/` into the image (or mount it) and set `MODEL_PATH` / `LABELS_PATH` if it lives elsewhere.

## How the other subsystems use it

Put `classification/src/` on the Python path (or install the package), then:

```python
from classification import ClassificationEngine

engine = ClassificationEngine.from_config()     # trained model, or demo mode if no weights yet
result = engine.classify("photo.jpg")           # file path (str/Path) or raw bytes
# -> ClassificationResult(material="plastic", category="recyclable", confidence=0.93,
#                         is_confident=True, top3=[("plastic", 0.93), ("metal", 0.04), ("glass", 0.01)])
```

Streamlit page (Subsystem 4), connecting this package to Data & Rules:

```python
import streamlit as st
from classification import ClassificationEngine
from data_rules import create_services

@st.cache_resource
def load():
    dal, rules = create_services()
    return ClassificationEngine.from_config(), dal, rules

clf, dal, rules = load()
uploaded = st.file_uploader("Photo", type=["jpg", "jpeg", "png"])
if uploaded:
    result = clf.classify(uploaded.getvalue())
    if not result.is_confident:
        st.warning("Not sure - please retake the photo.")
    else:
        rule = rules.get_rule(result.category, "DO")
        dal.save_result(result.material, result.category, result.confidence, "DO")
        st.success(f"{result.material} -> {rule.bin}")
```

Two additions the UI should handle:

- `clf.classify(...)` raises `InvalidImageError` for broken, too large or non-JPEG/PNG files.
  The message is written for users: `except InvalidImageError as e: st.error(str(e))`.
- `clf.is_demo_mode` is `True` when no trained weights were found. The engine then uses a
  `DummyClassifier` that always answers "plastic, 0.9". Show a banner so nobody mistakes it for a real result.

For tests or development without a model, build the engine directly:

```python
from classification import ClassificationEngine, DummyClassifier, ImagePreprocessor

engine = ClassificationEngine(DummyClassifier("organic", 0.8), ImagePreprocessor())
```

## Contract (agree this with the team before coding)

| Call | Returns / raises |
|---|---|
| `ClassificationEngine.from_config()` | `ClassificationEngine` (never fails because of missing weights) |
| `engine.classify(image)` | `ClassificationResult(material, category, confidence, is_confident, top3)` |
| `engine.is_demo_mode` | `bool` |
| `to_category(material)` | category `str`; `ValueError` for an unknown material |
| bad upload | `InvalidImageError` (user-readable message) |
| `MobileNetClassifier(...)` without weights | `ModelNotFoundError` |

- `material` is one of `paper`, `cardboard`, `plastic`, `metal`, `glass`, `organic`, `trash`.
- `category` is always `"recyclable"`, `"compostable"` or `"landfill"` (same as `data_rules.CATEGORIES`, checked by a test).

  | material | category |
  |---|---|
  | paper, cardboard, plastic, metal, glass | `recyclable` |
  | organic | `compostable` |
  | trash | `landfill` |

- `confidence` is the probability of the top material, a float from 0 to 1 (what `dal.save_result` expects).
- `is_confident` is `confidence >= CONFIDENCE_THRESHOLD`.
- `top3` has at most 3 `(material, probability)` pairs, highest first.
- `image` is a path or raw bytes; only JPEG and PNG up to `MAX_IMAGE_MB` are accepted.
- This package never imports `data_rules` and never touches the database. The UI connects the two.

## Design

| File | Content |
|---|---|
| `engine.py` | `ClassificationEngine`: composition of a preprocessor and a classifier |
| `classifiers.py` | `BaseClassifier` (abstract), `MobileNetClassifier`, `DummyClassifier` |
| `preprocessing.py` | `ImagePreprocessor`: checks the file, EXIF rotation, RGB, Resize 256, CenterCrop 224, ImageNet normalisation |
| `mapping.py` | `MATERIAL_TO_CATEGORY`, `to_category()` |
| `schemas.py` | `ClassificationResult` (frozen dataclass) |
| `config.py` | `ClassificationConfig.from_env()` |
| `exceptions.py` | `InvalidImageError`, `ModelNotFoundError` |

The engine only knows the `BaseClassifier` interface, so the real model and the dummy can be swapped
without touching the rest of the code.

## Training

The training scripts are in `training/` next to `src/` (not part of the app). Run all commands below from this folder.
`train.py` uses a CUDA GPU (Colab), an Apple Silicon GPU (MPS) or the CPU, whichever is available.

1. Download the dataset: `dataset-splits-custom.zip` (1.15 GB, MIT license) from
   [rootstrap-org/waste-classifier](https://huggingface.co/datasets/rootstrap-org/waste-classifier).
   It is TrashNet plus a `compost` class. Put it in `downloads/` (git-ignored).
2. Build `raw/<material>/` (renames `compost` to `organic`, merges its train/test, shrinks photos to 512 px):

   ```bash
   python training/prepare_dataset.py --zip downloads/dataset-splits-custom.zip --dest raw
   ```

3. Split 70/15/15, stratified, fixed seed (copies the files):

   ```bash
   python training/split_dataset.py --source raw --dest data
   ```

4. Train (on an M2 MacBook about 20 minutes; in Colab choose *Runtime → Change runtime type → GPU*
   and upload `data/` and `training/train.py`):

   ```bash
   python training/train.py --data-dir data --output-dir models --epochs-head 10 --epochs-finetune 10 --batch-size 32
   ```

   Stage 1 trains only the new head (features frozen, Adam lr 1e-3); stage 2 unfreezes the last 4
   feature blocks (lr 1e-4). The loss uses class weights, so small classes are not ignored.
   The epoch with the best validation accuracy is saved as `models/mobilenet_waste.pt`, plus
   `models/labels.json` (output order) and `models/history.json` (loss and accuracy per epoch).
5. Commit `models/` (9 MB). Always keep the `.pt` file and its `labels.json` together.

## Evaluation

```bash
python training/evaluate.py                         # test split in data/test
python training/evaluate.py --folder my_photos      # plus my_photos/<material>/*.jpg, reported separately
```

Every image goes through the same `ImagePreprocessor` and `MobileNetClassifier` as the app.
Output (printed and saved in `reports/`):

- overall accuracy, per-class accuracy, sklearn classification report (`report_test.txt`)
- confusion matrix (`confusion_matrix_test.png`)
- threshold table: for thresholds 0.40 to 0.90, the share of photos that would be shown (coverage)
  and the accuracy on those. Use it to choose `CONFIDENCE_THRESHOLD`.

With `--folder` the same files are written with the name `real_world`.

## Results (current model)

Dataset: 3,248 photos (cardboard 433, glass 134, metal 313, organic 769, paper 564, plastic 308, trash 727),
split into 2,280 train / 484 val / 484 test. Best epoch: fine-tuning epoch 10, validation accuracy 0.907.

**Test split (484 photos never seen in training): accuracy 0.897.**

| material | accuracy | n |
|---|---|---|
| cardboard | 0.859 | 64 |
| glass | 0.950 | 20 |
| metal | 0.913 | 46 |
| organic | 1.000 | 115 |
| paper | 0.929 | 84 |
| plastic | 0.913 | 46 |
| trash | 0.761 | 109 |

Most mistakes are `trash` photos predicted as `plastic` (10) or `paper` (7), and `cardboard` predicted as `paper` (7).
See `reports/confusion_matrix_test.png` and `reports/report_test.txt`.

Threshold table (test split):

| threshold | coverage | accuracy on kept |
|---|---|---|
| 0.50 | 96.5% | 0.912 |
| **0.60** | **92.8%** | **0.920** |
| 0.70 | 88.2% | 0.937 |
| 0.80 | 83.7% | 0.943 |
| 0.90 | 75.8% | 0.959 |

`CONFIDENCE_THRESHOLD` stays at **0.6**: 93 % of photos get an answer, and 92 % of those answers are correct.
Set it to 0.7 if a wrong bin is worse than asking the user to retake the photo.

One prediction takes about 0.1 s on a laptop CPU (`test_one_inference_under_one_second_on_cpu`).

## Known limits

- **TrashNet photos have a plain white background** and one centred object. Real photos from a kitchen
  have clutter, shadows and other lighting, so accuracy on them is usually lower than on the test split.
  Evaluate with `--folder` on your own photos and report both numbers.
- **TrashNet has no organic class.** The `organic` images come from a second source with different
  backgrounds and camera styles, so the model may partly learn "which dataset" instead of "which material".
  The perfect 1.000 on organic is a warning sign for this, not proof of a perfect model.
- `glass` has only 134 photos, so its test accuracy rests on 20 images.
- One item per photo. A photo with several items gets the label of the most visible one.
- The category is only as good as the material. In Dortmund "recyclable" still means yellow bin,
  blue paper bin or glass container; `result.material` is there so the UI or the rules can pick the exact bin.
- The demo mode answer (`DummyClassifier`) is fixed and has no meaning; check `is_demo_mode`.
