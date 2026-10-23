"""Engine and session setup."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import database_url
from .models import Base


def _enable_foreign_keys(dbapi_conn, _record):
    # SQLite ignores foreign keys unless this is switched on per connection.
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def make_engine(url: str | None = None, **kwargs) -> Engine:
    url = url or database_url()
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(engine, expire_on_commit=False)


def create_services(url: str | None = None, seed: bool = True):
    """Build everything the other subsystems need: (DataAccessLayer, RuleEngine)."""
    from .data_access import DataAccessLayer
    from .rule_engine import RuleEngine

    engine = make_engine(url)
    init_db(engine)
    dal = DataAccessLayer(make_session_factory(engine))
    if seed:
        from .seed import seed_database
        seed_database(dal)
    return dal, RuleEngine(dal)
