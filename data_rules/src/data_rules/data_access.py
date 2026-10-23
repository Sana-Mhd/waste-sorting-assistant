"""Data access layer: the only door to the database.

Subsystems 1, 3 and 4 call these methods and get plain dataclasses back.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from .config import CATEGORIES
from .models import ClassificationResultRow, Item, Region, RuleRow, User
from .schemas import ClassificationRecord, Rule


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _check_category(category: str) -> None:
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")


class DataAccessLayer:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    # ---- regions and rules (configuration) ---------------------------------

    def add_region(self, code: str, name: str) -> None:
        """Create the region, or update its name if it already exists."""
        code = code.strip().upper()
        if not code or not name.strip():
            raise ValueError("region code and name must not be empty")
        with self._sf() as s:
            region = s.get(Region, code)
            if region is None:
                s.add(Region(code=code, name=name.strip()))
            else:
                region.name = name.strip()
            s.commit()

    def list_regions(self) -> list[tuple[str, str]]:
        with self._sf() as s:
            rows = s.scalars(select(Region).order_by(Region.name)).all()
            return [(r.code, r.name) for r in rows]

    def region_exists(self, code: str) -> bool:
        with self._sf() as s:
            return s.get(Region, code.strip().upper()) is not None

    def set_rule(self, region_code: str, category: str, bin: str, reason: str) -> None:
        """Insert or update the rule for (region, category). Safe to call twice."""
        _check_category(category)
        region_code = region_code.strip().upper()
        with self._sf() as s:
            if s.get(Region, region_code) is None:
                raise ValueError(f"unknown region {region_code!r}, call add_region first")
            row = s.scalar(
                select(RuleRow).where(
                    RuleRow.region_code == region_code, RuleRow.category == category
                )
            )
            if row is None:
                s.add(RuleRow(region_code=region_code, category=category, bin=bin, reason=reason))
            else:
                row.bin, row.reason = bin, reason
            s.commit()

    def get_rule(self, category: str, region_code: str) -> Rule | None:
        """Exact lookup. Returns None if there is no rule for this pair."""
        _check_category(category)
        with self._sf() as s:
            row = s.scalar(
                select(RuleRow).where(
                    RuleRow.region_code == region_code.strip().upper(),
                    RuleRow.category == category,
                )
            )
            return self._rule(row) if row else None

    def get_rules(self, region_code: str) -> list[Rule]:
        with self._sf() as s:
            rows = s.scalars(
                select(RuleRow)
                .where(RuleRow.region_code == region_code.strip().upper())
                .order_by(RuleRow.category)
            ).all()
            return [self._rule(r) for r in rows]

    # ---- users and classification results ----------------------------------

    def get_or_create_user(self, username: str) -> int:
        username = username.strip()
        if not username:
            raise ValueError("username must not be empty")
        with self._sf() as s:
            user = s.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(username=username)
                s.add(user)
                s.commit()
            return user.id

    def save_result(
        self,
        item: str,
        category: str,
        confidence: float,
        region_code: str,
        user_id: int | None = None,
    ) -> int:
        """Store one classification and return its id."""
        _check_category(category)
        item = item.strip().lower()
        if not item:
            raise ValueError("item must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        region_code = region_code.strip().upper()
        with self._sf() as s:
            if s.get(Region, region_code) is None:
                raise ValueError(f"unknown region {region_code!r}")
            item_row = s.scalar(select(Item).where(Item.name == item))
            if item_row is None:
                item_row = Item(name=item)
                s.add(item_row)
                s.flush()
            row = ClassificationResultRow(
                user_id=user_id,
                item_id=item_row.id,
                region_code=region_code,
                category=category,
                confidence=confidence,
            )
            s.add(row)
            s.commit()
            return row.id

    def get_results(
        self,
        region_code: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ClassificationRecord]:
        """Stored results, oldest first. Filters are optional.

        Subsystem 3 uses this for composition, recycling rate and trend.
        """
        since, until = _to_naive_utc(since), _to_naive_utc(until)
        stmt = select(ClassificationResultRow).order_by(
            ClassificationResultRow.created_at, ClassificationResultRow.id
        )
        if region_code:
            stmt = stmt.where(ClassificationResultRow.region_code == region_code.strip().upper())
        if since:
            stmt = stmt.where(ClassificationResultRow.created_at >= since)
        if until:
            stmt = stmt.where(ClassificationResultRow.created_at <= until)
        with self._sf() as s:
            return [
                ClassificationRecord(
                    id=r.id,
                    item=r.item.name,
                    category=r.category,
                    confidence=r.confidence,
                    region_code=r.region_code,
                    created_at=r.created_at,
                )
                for r in s.scalars(stmt).all()
            ]

    # ---- helpers -------------------------------------------------------------

    @staticmethod
    def _rule(row: RuleRow) -> Rule:
        return Rule(category=row.category, region_code=row.region_code, bin=row.bin, reason=row.reason)
