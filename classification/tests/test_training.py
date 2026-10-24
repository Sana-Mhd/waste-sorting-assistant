"""Tests for the helper logic of the training scripts (no GPU, no real dataset needed)."""
import io
import sys
import zipfile
from pathlib import Path

import pytest
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from training.prepare_dataset import FOLDER_TO_MATERIAL, MAX_SIDE, prepare  # noqa: E402
from training.split_dataset import split_dataset, split_files  # noqa: E402
from training.train import compute_class_weights  # noqa: E402

from classification import MATERIAL_TO_CATEGORY  # noqa: E402  (src/ is on the path via conftest.py)


def make_class_folder(root: Path, name: str, count: int) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    for i in range(count):
        (folder / f"{name}_{i:03d}.jpg").write_bytes(b"x")


def test_split_files_is_70_15_15_without_overlap():
    files = [Path(f"img_{i}.jpg") for i in range(100)]
    parts = split_files(files, seed=42)
    assert [len(parts[s]) for s in ("train", "val", "test")] == [70, 15, 15]
    assert set(parts["train"]) | set(parts["val"]) | set(parts["test"]) == set(files)


def test_split_files_is_repeatable_with_same_seed():
    files = [Path(f"img_{i}.jpg") for i in range(50)]
    assert split_files(files, seed=1) == split_files(list(reversed(files)), seed=1)
    assert split_files(files, seed=1) != split_files(files, seed=2)


def test_split_dataset_is_stratified(tmp_path):
    source = tmp_path / "raw"
    make_class_folder(source, "paper", 100)
    make_class_folder(source, "glass", 40)
    (source / "glass" / "notes.txt").write_text("not an image")

    counts = split_dataset(source, tmp_path / "data")

    assert counts["paper"] == {"train": 70, "val": 15, "test": 15}
    assert counts["glass"] == {"train": 28, "val": 6, "test": 6}
    assert len(list((tmp_path / "data" / "test" / "glass").iterdir())) == 6


def test_split_dataset_refuses_to_overwrite(tmp_path):
    source = tmp_path / "raw"
    make_class_folder(source, "paper", 10)
    split_dataset(source, tmp_path / "data")
    with pytest.raises(FileExistsError):
        split_dataset(source, tmp_path / "data")


def test_class_weights_favour_rare_classes():
    weights = compute_class_weights([0] * 80 + [1] * 20, num_classes=2)
    assert weights[1] > weights[0]
    assert weights.tolist() == pytest.approx([100 / (2 * 80), 100 / (2 * 20)])
    assert weights.dtype == torch.float32


def test_class_weights_missing_class_raises():
    with pytest.raises(ValueError, match="no training images"):
        compute_class_weights([0, 0, 1], num_classes=3)


def test_prepare_maps_every_folder_to_a_known_material():
    assert set(FOLDER_TO_MATERIAL.values()) == set(MATERIAL_TO_CATEGORY)


def test_prepare_renames_merges_and_resizes(tmp_path):
    zip_path = tmp_path / "data.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for split in ("train", "test"):
            for folder in ("compost", "glass"):
                buffer = io.BytesIO()
                Image.new("RGB", (1200, 900), "red").save(buffer, "JPEG")
                archive.writestr(f"dataset_splits/{split}/{folder}/img1.jpg", buffer.getvalue())
        archive.writestr("dataset_splits/train/glass/readme.txt", "not an image")

    counts = prepare(zip_path, tmp_path / "raw")

    assert counts == {"organic": 2, "glass": 2}           # same file name in train/ and test/ is kept twice
    saved = Image.open(next((tmp_path / "raw" / "organic").iterdir()))
    assert max(saved.size) == MAX_SIDE
