"""Errors raised by the classification engine.

The messages are written so the web interface can show them to the user as they are.
"""


class InvalidImageError(Exception):
    """The uploaded file is not a usable photo (wrong format, too large, broken)."""


class ModelNotFoundError(Exception):
    """The trained model weights or the labels file could not be found."""
