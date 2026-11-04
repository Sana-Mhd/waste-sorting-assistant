"""The error class of Data & Rules."""


class DataRulesError(ValueError):
    """Bad input or a broken rule file, e.g. an unknown category or an unknown region.

    It is also a ValueError, so code that already catches that keeps working.
    """
