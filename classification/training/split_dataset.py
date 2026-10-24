"""Split a folder of class subfolders into train/val/test (70/15/15), stratified per class.

    source/                      data/
      paper/  a.jpg ...    ->      train/paper/ ...   val/paper/ ...   test/paper/ ...
      glass/  ...                  train/glass/ ...   ...

Files are copied, the source stays untouched. The same --seed always gives the same split.

Usage:
    python training/split_dataset.py --source raw_dataset --dest data
"""
import argparse
import logging
import random
import shutil
from pathlib import Path

logger = logging.getLogger("split_dataset")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SPLITS = ("train", "val", "test")


def split_files(files: list[Path], seed: int, val_ratio: float = 0.15, test_ratio: float = 0.15) -> dict[str, list[Path]]:
    """Shuffle the files of ONE class with a fixed seed and cut them into train/val/test."""
    shuffled = sorted(files)                     # sort first so the result does not depend on the OS
    random.Random(seed).shuffle(shuffled)
    n_val = int(len(shuffled) * val_ratio)
    n_test = int(len(shuffled) * test_ratio)
    return {
        "val": shuffled[:n_val],
        "test": shuffled[n_val:n_val + n_test],
        "train": shuffled[n_val + n_test:],
    }


def split_dataset(source: Path, dest: Path, seed: int = 42) -> dict[str, dict[str, int]]:
    """Copy every class folder of `source` into dest/{train,val,test}/<class>/.

    Returns:
        Number of copied files per class and split, e.g. {"paper": {"train": 70, ...}}.

    Raises:
        FileNotFoundError: if `source` does not exist.
        FileExistsError: if `dest` already contains a split, so nothing is mixed up by accident.
    """
    if not source.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source}")
    for split in SPLITS:
        if (dest / split).exists() and any((dest / split).iterdir()):
            raise FileExistsError(f"{dest / split} is not empty. Delete it or choose another --dest.")

    counts: dict[str, dict[str, int]] = {}
    for class_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        files = [p for p in class_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
        skipped = sum(1 for p in class_dir.iterdir() if p.is_file() and p.suffix.lower() not in IMAGE_EXTENSIONS)
        if skipped:
            logger.warning("%s: skipped %d files that are not JPEG/PNG", class_dir.name, skipped)
        if not files:
            logger.warning("%s: no images, class skipped", class_dir.name)
            continue

        parts = split_files(files, seed)
        for split, chosen in parts.items():
            target = dest / split / class_dir.name
            target.mkdir(parents=True, exist_ok=True)
            for file in chosen:
                shutil.copy2(file, target / file.name)
        counts[class_dir.name] = {split: len(parts[split]) for split in SPLITS}
        if not parts["val"] or not parts["test"]:
            logger.warning("%s: only %d images, val or test is empty", class_dir.name, len(files))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="folder with one subfolder per class")
    parser.add_argument("--dest", type=Path, default=Path("data"), help="output folder (default: data)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    counts = split_dataset(args.source, args.dest, args.seed)

    logger.info("%-12s %6s %6s %6s", "class", *SPLITS)
    for name, per_split in counts.items():
        logger.info("%-12s %6d %6d %6d", name, *(per_split[s] for s in SPLITS))
    logger.info("Done. Split written to %s", args.dest)


if __name__ == "__main__":
    main()
