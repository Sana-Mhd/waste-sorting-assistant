"""SQLAlchemy tables: user, item, classification_result, region, rule."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Naive UTC time. SQLite has no timezone type, so we store UTC consistently."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Region(Base):
    __tablename__ = "region"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)   # "DO"
    name: Mapped[str] = mapped_column(String(80))                     # "Dortmund"

    rules: Mapped[list["RuleRow"]] = relationship(back_populates="region")


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)       # "plastic bottle"


class RuleRow(Base):
    """One row per (region, category): which bin and why."""
    __tablename__ = "rule"
    __table_args__ = (UniqueConstraint("region_code", "category", name="uq_rule_region_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    region_code: Mapped[str] = mapped_column(ForeignKey("region.code"))
    category: Mapped[str] = mapped_column(String(16))
    bin: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(300))

    region: Mapped[Region] = relationship(back_populates="rules")


class ClassificationResultRow(Base):
    __tablename__ = "classification_result"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_confidence_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"))
    region_code: Mapped[str] = mapped_column(ForeignKey("region.code"))
    category: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    item: Mapped[Item] = relationship()
