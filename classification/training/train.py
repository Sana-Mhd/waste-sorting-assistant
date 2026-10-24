"""Fine-tune MobileNetV2 on the waste dataset. Meant to run in Google Colab with a GPU.

Expects data/{train,val}/<class>/ (see split_dataset.py). Two stages:
  1. freeze the pretrained features, train only the new head   (Adam, lr 1e-3)
  2. unfreeze the last 4 feature blocks and fine-tune            (Adam, lr 1e-4)
The epoch with the best validation accuracy is saved to models/mobilenet_waste.pt,
the class names (= model output order) to models/labels.json.

This file is standalone on purpose: it does not import the classification package,
so it can be copied to Colab on its own.

Usage:
    python training/train.py --data-dir data --output-dir models --epochs-head 10 --epochs-finetune 10
"""
import argparse
import json
import logging
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

logger = logging.getLogger("train")

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

TRAIN_TRANSFORM = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

# Must be the same as classification.preprocessing.ImagePreprocessor (what the app does).
EVAL_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def set_seed(seed: int) -> None:
    """Make the run repeatable (as far as the GPU allows)."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def compute_class_weights(targets: list[int], num_classes: int) -> torch.Tensor:
    """Weight each class by total / (num_classes * count), so rare classes count more in the loss."""
    counts = Counter(targets)
    missing = [c for c in range(num_classes) if counts[c] == 0]
    if missing:
        raise ValueError(f"Classes {missing} have no training images.")
    total = len(targets)
    return torch.tensor([total / (num_classes * counts[c]) for c in range(num_classes)], dtype=torch.float32)


def build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    """MobileNetV2 with a new last layer for our classes (same layout as MobileNetClassifier)."""
    model = models.mobilenet_v2(weights="IMAGENET1K_V1" if pretrained else None)
    model.classifier[1] = nn.Linear(1280, num_classes)
    return model


def run_epoch(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device,
              optimizer: torch.optim.Optimizer | None = None) -> tuple[float, float]:
    """One pass over the loader. Trains if an optimizer is given, otherwise only evaluates.

    Returns:
        (average loss, accuracy)
    """
    training = optimizer is not None
    model.train(training)
    total_loss, correct, seen = 0.0, 0, 0
    with torch.set_grad_enabled(training):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * labels.size(0)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            seen += labels.size(0)
    return total_loss / seen, correct / seen


def train_stage(name: str, model: nn.Module, loaders: dict[str, DataLoader], criterion: nn.Module,
                optimizer: torch.optim.Optimizer, epochs: int, device: torch.device,
                best: dict, model_file: Path, history: list[dict]) -> None:
    """Train for some epochs and save the weights whenever validation accuracy improves."""
    for epoch in range(1, epochs + 1):
        start = time.time()
        train_loss, train_acc = run_epoch(model, loaders["train"], criterion, device, optimizer)
        val_loss, val_acc = run_epoch(model, loaders["val"], criterion, device)
        history.append({"stage": name, "epoch": epoch, "train_loss": train_loss, "train_acc": train_acc,
                        "val_loss": val_loss, "val_acc": val_acc})
        logger.info("[%s %2d/%d] train loss %.3f acc %.3f | val loss %.3f acc %.3f | %.0fs",
                    name, epoch, epochs, train_loss, train_acc, val_loss, val_acc, time.time() - start)

        if val_acc > best["val_acc"]:
            best.update(val_acc=val_acc, stage=name, epoch=epoch)
            state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
            torch.save(state, model_file)
            logger.info("  new best model saved (val acc %.3f)", val_acc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    parser.add_argument("--epochs-head", type=int, default=10, help="stage 1 epochs (frozen features)")
    parser.add_argument("--epochs-finetune", type=int, default=10, help="stage 2 epochs (last 4 blocks)")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-pretrained", action="store_true", help="random start (only for quick tests)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    set_seed(args.seed)
    if torch.cuda.is_available():
        device = torch.device("cuda")                # Colab GPU
    elif torch.backends.mps.is_available():
        device = torch.device("mps")                 # Apple Silicon GPU
    else:
        device = torch.device("cpu")
    logger.info("Device: %s", device)

    for split in ("train", "val"):
        if not (args.data_dir / split).is_dir():
            raise SystemExit(f"Missing {args.data_dir / split}. Run training/split_dataset.py first.")
    train_set = datasets.ImageFolder(args.data_dir / "train", transform=TRAIN_TRANSFORM)
    val_set = datasets.ImageFolder(args.data_dir / "val", transform=EVAL_TRANSFORM)
    if train_set.classes != val_set.classes:
        raise SystemExit(f"train and val have different classes: {train_set.classes} vs {val_set.classes}")
    classes = train_set.classes
    logger.info("Classes: %s | train %d images | val %d images", classes, len(train_set), len(val_set))

    generator = torch.Generator().manual_seed(args.seed)
    loaders = {
        "train": DataLoader(train_set, batch_size=args.batch_size, shuffle=True,
                            num_workers=args.num_workers, generator=generator),
        "val": DataLoader(val_set, batch_size=args.batch_size, num_workers=args.num_workers),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_file = args.output_dir / "mobilenet_waste.pt"
    (args.output_dir / "labels.json").write_text(json.dumps(classes, indent=2))

    model = build_model(len(classes), pretrained=not args.no_pretrained).to(device)
    weights = compute_class_weights(train_set.targets, len(classes)).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    best = {"val_acc": -1.0, "stage": None, "epoch": None}
    history: list[dict] = []

    # Stage 1: only the new head learns.
    for param in model.features.parameters():
        param.requires_grad = False
    optimizer = torch.optim.Adam(model.classifier.parameters(), lr=1e-3)
    train_stage("head", model, loaders, criterion, optimizer, args.epochs_head, device, best, model_file, history)

    # Stage 2: also adapt the last 4 feature blocks, with a smaller learning rate.
    for param in model.features[-4:].parameters():
        param.requires_grad = True
    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable, lr=1e-4)
    train_stage("finetune", model, loaders, criterion, optimizer, args.epochs_finetune, device, best, model_file, history)

    (args.output_dir / "history.json").write_text(json.dumps(history, indent=2))
    logger.info("Best val acc %.3f (%s epoch %s). Saved %s and labels.json",
                best["val_acc"], best["stage"], best["epoch"], model_file)


if __name__ == "__main__":
    main()
