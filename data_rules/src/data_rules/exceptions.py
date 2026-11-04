"""Errors raised by Data & Rules.

Catch DataRulesError to handle every problem of this subsystem in one place.
Bad input and bad rule files are also a ValueError (and a missing rules folder a
FileNotFoundError), so code that already catches those keeps working.
"""


class DataRulesError(Exception):
    """Base class of every error of Data & Rules."""


class InvalidDataError(DataRulesError, ValueError):
    """A value is not allowed, e.g. an unknown category or a confidence above 1."""


class UnknownRegionError(InvalidDataError):
    """The region code is not in the database."""


class RuleFileError(DataRulesError, ValueError):
    """A rule file cannot be read or has the wrong content."""


class NoRuleFilesError(RuleFileError, FileNotFoundError):
    """The rules folder contains no rule files."""


class DatabaseError(DataRulesError):
    """The database could not carry out the request. The message is written for users."""
