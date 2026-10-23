import sys
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_rules.data_access import DataAccessLayer  # noqa: E402
from data_rules.database import init_db, make_engine, make_session_factory  # noqa: E402
from data_rules.rule_engine import RuleEngine  # noqa: E402
from data_rules.seed import seed_database  # noqa: E402


@pytest.fixture
def dal():
    """Fresh in-memory database for every test."""
    engine = make_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    init_db(engine)
    layer = DataAccessLayer(make_session_factory(engine))
    seed_database(layer)
    return layer


@pytest.fixture
def engine_rules(dal):
    return RuleEngine(dal)
