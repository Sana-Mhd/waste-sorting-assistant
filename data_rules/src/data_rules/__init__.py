"""Subsystem 2: Data & Rules.

Public API for the other subsystems:

    from data_rules import create_services

    dal, engine = create_services()          # uses DATABASE_URL or data/waste.db
    rule = engine.get_rule("recyclable", "DO")
    dal.save_result("plastic bottle", "recyclable", 0.93, "DO")
"""
from .config import CATEGORIES, DEFAULT_DATABASE_URL
from .data_access import DataAccessLayer
from .database import create_services, init_db, make_session_factory
from .rule_engine import RuleEngine
from .schemas import ClassificationRecord, Rule

__all__ = [
    "CATEGORIES",
    "DEFAULT_DATABASE_URL",
    "ClassificationRecord",
    "DataAccessLayer",
    "Rule",
    "RuleEngine",
    "create_services",
    "init_db",
    "make_session_factory",
]
