"""Preprocessing: check an uploaded photo and turn it into a model input tensor."""
import io
import logging
from pathlib import Path

import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from torchvision import transforms

from .config import DEFAULT_MAX_IMAGE_MB
from .exceptions import InvalidImageError
from .schemas import ImageInput

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = ("JPEG", "PNG")

# ImageNet statistics, because MobileNetV2 was pretrained on ImageNet.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class ImagePreprocessor:
    """Validate a photo (path or bytes) and convert it to a tensor of shape (1, 3, 224, 224)."""

    def __init__(self, max_image_mb: float = DEFAULT_MAX_IMAGE_MB) -> None:
        if max_image_mb <= 0:
            raise ValueError(f"max_image_mb must be greater than 0, got {max_image_mb}.")
        self.max_image_mb = max_image_mb
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])

    def process(self, image: ImageInput) -> torch.Tensor:
        """Return the model input tensor (1, 3, 224, 224) for a photo.

        Raises:
            InvalidImageError: if the file is missing, too large, broken or not JPEG/PNG.
        """
        picture = self.load_image(image)
        return self.transform(picture).unsqueeze(0)

    def load_image(self, image: ImageInput) -> Image.Image:
        """Read and check a photo; return it upright (EXIF orientation applied) and in RGB.

        Raises:
            InvalidImageError: if the file is missing, too large, broken or not JPEG/PNG.
        """
        data = self._read_bytes(image)
        try:
            picture = Image.open(io.BytesIO(data))
            picture.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            logger.warning("Could not decode image: %s", error)
            raise InvalidImageError("This file is not a readable image. Please upload a JPEG or PNG photo.") from error

        if picture.format not in ALLOWED_FORMATS:
            raise InvalidImageError(
                f"Images in {picture.format} format are not supported. Please upload a JPEG or PNG photo."
            )

        picture = ImageOps.exif_transpose(picture)
        return picture.convert("RGB")

    def _read_bytes(self, image: ImageInput) -> bytes:
        """Get the raw bytes from a path or bytes and enforce the size limit."""
        max_bytes = int(self.max_image_mb * 1024 * 1024)

        if isinstance(image, (bytes, bytearray)):
            data = bytes(image)
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if not path.is_file():
                raise InvalidImageError(f"Image file not found: {path}")
            if path.stat().st_size > max_bytes:
                raise InvalidImageError(self._too_large_message())
            data = path.read_bytes()
        else:
            raise TypeError(f"Expected a file path or bytes, got {type(image).__name__}.")

        if len(data) == 0:
            raise InvalidImageError("The file is empty. Please upload a JPEG or PNG photo.")
        if len(data) > max_bytes:
            raise InvalidImageError(self._too_large_message())
        return data

    def _too_large_message(self) -> str:
        return f"The image is too large. The maximum size is {self.max_image_mb:g} MB."
