"""Errors raised inside subsystem 3.

The coach never lets an error reach the user: `CoachService.explain` always
returns a text. These exceptions exist so the internal parts can say what went
wrong and the tests can check it.
"""


class CoachError(Exception):
    """Base class for every error of the AI coach."""


class LanguageModelUnavailable(CoachError):
    """The language model could not be reached or answered with an error."""


class CacheUnavailable(CoachError):
    """The explanation cache could not be opened or written."""
