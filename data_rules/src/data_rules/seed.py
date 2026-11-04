"""Fill the database from the rule files in the rules directory.

Every region is one JSON file (see rules/dortmund.json). To add a city you add
a file, you do not change any code. Running the seed again never creates
duplicates, it updates the existing rows.

The rules directory is src/data_rules/rules by default. Set RULES_DIR to use
another folder.
"""
import json
import os
from pathlib import Path

from .config import CATEGORIES
from .data_access import DataAccessLayer
from .exceptions import DataRulesError

DEFAULT_RULES_DIR = Path(__file__).parent / "rules"


def rules_dir() -> Path:
    return Path(os.environ.get("RULES_DIR", DEFAULT_RULES_DIR))


def load_rule_files(directory: Path | str | None = None) -> list[dict]:
    """Read and validate every *.json file in the directory.

    Raises:
        FileNotFoundError: if the directory contains no rule files.
        DataRulesError: if a file is not valid JSON or has the wrong content.
    """
    directory = Path(directory) if directory else rules_dir()
    files = sorted(directory.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no rule files found in {directory}")
    result = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            code, name = data["region"]["code"], data["region"]["name"]
            rules = data["rules"]
            if not code or not name:
                raise ValueError("region code and name must not be empty")
            for rule in rules:
                if rule["category"] not in CATEGORIES:
                    raise ValueError(f"unknown category {rule['category']!r}")
                if not rule["bin"] or not rule["reason"]:
                    raise ValueError("bin and reason must not be empty")
        except (KeyError, TypeError, ValueError) as exc:
            raise DataRulesError(f"invalid rule file {path.name}: {exc}") from exc
        result.append(data)
    return result


class RuleFileLoader:
    """Loads the rule files of one folder."""

    def __init__(self, directory: Path | str | None = None) -> None:
        """
        Args:
            directory: the folder with the rule files; by default rules_dir().
        """
        self.directory = directory or rules_dir()

    @property
    def directory(self) -> Path:
        """The folder with the rule files."""
        return self._directory

    @directory.setter
    def directory(self, directory: Path | str) -> None:
        self._directory = Path(directory)

    def load(self) -> list[dict]:
        """Read and validate every rule file. See load_rule_files for the errors."""
        return load_rule_files(self.directory)


def seed_database(dal: DataAccessLayer, directory: Path | str | None = None) -> None:
    for data in RuleFileLoader(directory).load():
        code = data["region"]["code"]
        dal.add_region(code, data["region"]["name"])
        for rule in data["rules"]:
            dal.set_rule(code, rule["category"], rule["bin"], rule["reason"])


if __name__ == "__main__":
    from .database import init_db, make_engine, make_session_factory

    engine = make_engine()
    init_db(engine)
    seed_database(DataAccessLayer(make_session_factory(engine)))
    print("Database seeded.")
