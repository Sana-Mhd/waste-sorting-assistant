"""Turn the downloaded dataset zip into raw/<material>/ for split_dataset.py.

Source: https://huggingface.co/datasets/rootstrap-org/waste-classifier (MIT license),
file dataset-splits-custom.zip = TrashNet + a "compost" class, already split into train/test.
We merge its splits (split_dataset.py makes our own 70/15/15 split), rename the folders
to our material names and shrink every photo to at most 512 px, so training is faster.

Usage:
    python training/prepare_dataset.py --zip downloads/dataset-splits-custom.zip --dest raw
"""
import argparse
import logging
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger("prepare_dataset")

# Folder name in the zip -> our material name (see src/classification/mapping.py).
FOLDER_TO_MATERIAL = {
    "cardboard": "cardboard",
    "compost": "organic",
    "glass": "glass",
    "metal": "metal",
    "paper": "paper",
    "plastic": "plastic",
    "trash": "trash",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_SIDE = 512


def prepare(zip_path: Path, dest: Path) -> Counter:
    """Extract, rename and resize all images. Returns the number of images per material."""
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} is not empty. Delete it first.")
    counts: Counter = Counter()
    with zipfile.ZipFile(zip_path) as archive:
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if entry.is_dir() or path.suffix.lower() not in IMAGE_EXTENSIONS or "__MACOSX" in path.parts:
                continue
            material = FOLDER_TO_MATERIAL.get(path.parent.name.lower())
            if material is None:
                logger.warning("Skipping %s: unknown class folder", entry.filename)
                continue
            try:
                picture = Image.open(BytesIO(archive.read(entry)))
                picture = ImageOps.exif_transpose(picture).convert("RGB")
            except (UnidentifiedImageError, OSError) as error:
                logger.warning("Skipping broken image %s: %s", entry.filename, error)
                continue
            picture.thumbnail((MAX_SIDE, MAX_SIDE))
            target = dest / material
            target.mkdir(parents=True, exist_ok=True)
            # Prefix with the original split so equal file names from train/ and test/ do not clash.
            split = path.parts[-3] if len(path.parts) >= 3 else "all"
            picture.save(target / f"{split}_{path.stem}.jpg", quality=92)
            counts[material] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--dest", type=Path, default=Path("raw"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    counts = prepare(args.zip, args.dest)
    for material, count in sorted(counts.items()):
        logger.info("%-10s %5d", material, count)
    logger.info("Total %d images in %s", sum(counts.values()), args.dest)


if __name__ == "__main__":
    main()
