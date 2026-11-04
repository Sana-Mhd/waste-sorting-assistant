"""Settings of the web interface, read from the environment."""
import os
from dataclasses import dataclass

DEFAULT_REGION = "DO"
APP_TITLE = "Waste Sorting & Recycling Assistant"


@dataclass(frozen=True)
class WebConfig:
    """Everything the web interface needs at start-up."""

    database_url: str | None = None   # None: data_rules uses its own default (data/waste.db)
    default_region: str = DEFAULT_REGION
    title: str = APP_TITLE

    @classmethod
    def from_env(cls) -> "WebConfig":
        """Build the settings from DATABASE_URL and DEFAULT_REGION."""
        return cls(
            database_url=os.getenv("DATABASE_URL", "").strip() or None,
            default_region=os.getenv("DEFAULT_REGION", DEFAULT_REGION).strip() or DEFAULT_REGION,
        )


def resolve_region(value: str, regions: list[tuple[str, str]]) -> str:
    """Turn a region code or name ("DO", "do", "Dortmund") into a known region code.

    Falls back to the first known region, so a typo in the settings never breaks the app.

    Args:
        value: what the settings say.
        regions: (code, name) pairs from data_rules, e.g. [("DO", "Dortmund")].
    """
    wanted = value.strip().lower()
    for code, name in regions:
        if wanted in (code.lower(), name.lower()):
            return code
    return regions[0][0] if regions else value.strip().upper()
