"""Settings. The database location is read from the environment, never hard-coded."""
import os

# The three categories the classification engine (Subsystem 1) can return.
CATEGORIES = ("recyclable", "compostable", "landfill")

DEFAULT_DATABASE_URL = "sqlite:///data/waste.db"


def database_url() -> str:
    """The database address from DATABASE_URL, or the local SQLite file by default."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
