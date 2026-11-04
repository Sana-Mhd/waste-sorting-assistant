"""Errors raised by the web interface.

The messages are shown on the page as they are, so they are written for users.
"""


class WebError(Exception):
    """Base class of every error of the web interface."""


class ServiceStartupError(WebError):
    """One of the three subsystems could not be started (model, database or coach)."""
