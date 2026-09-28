from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def str_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda values: [v.value for v in values])


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class User(Timestamps, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    gardens: Mapped[list["Garden"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


# Shared, read-only catalogue. Rows are maintained by the seed loader (D007).


class CropFamily(Base):
    __tablename__ = "crop_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    names: Mapped[dict[str, str]] = mapped_column(JSON)


class Crop(Base):
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint("default_start_month BETWEEN 1 AND 12", name="start_month_range"),
        CheckConstraint("default_end_month BETWEEN 1 AND 12", name="end_month_range"),
        CheckConstraint("default_start_year_offset IN (-1, 0)", name="start_year_offset"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    names: Mapped[dict[str, str]] = mapped_column(JSON)
    family_id: Mapped[int] = mapped_column(ForeignKey("crop_families.id"), index=True)
    default_start_month: Mapped[int] = mapped_column(Integer)
    default_end_month: Mapped[int] = mapped_column(Integer)
    default_start_year_offset: Mapped[int] = mapped_column(Integer, default=0)
    family: Mapped[CropFamily] = relationship()


class RotationRule(Base):
    __tablename__ = "rotation_rules"
    __table_args__ = (
        CheckConstraint("(crop_id IS NULL) <> (family_id IS NULL)", name="one_target"),
        CheckConstraint("preferred_gap_years >= 0", name="gap_non_negative"),
        CheckConstraint("weight > 0", name="weight_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crop_id: Mapped[int | None] = mapped_column(ForeignKey("crops.id"), unique=True)
    family_id: Mapped[int | None] = mapped_column(ForeignKey("crop_families.id"), unique=True)
    preferred_gap_years: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class Compatibility(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class CompanionRule(Base):
    __tablename__ = "companion_rules"
    __table_args__ = (
        UniqueConstraint("crop_a_id", "crop_b_id"),
        CheckConstraint("crop_a_id < crop_b_id", name="ordered_pair"),
        CheckConstraint("weight > 0", name="weight_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crop_a_id: Mapped[int] = mapped_column(ForeignKey("crops.id"))
    crop_b_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    compatibility: Mapped[Compatibility] = mapped_column(str_enum(Compatibility, "compatibility"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)


# Private data, owned through Garden.user_id.


def window_order() -> CheckConstraint:
    """Windows are first-of-month dates (D012); the API schemas guarantee the day."""
    return CheckConstraint("start_month <= end_month", name="window_order")


class Garden(Timestamps, Base):
    __tablename__ = "gardens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    owner: Mapped[User] = relationship(back_populates="gardens")
    beds: Mapped[list["Bed"]] = relationship(
        back_populates="garden", cascade="all, delete-orphan", passive_deletes=True
    )
    plans: Mapped[list["Plan"]] = relationship(
        back_populates="garden", cascade="all, delete-orphan", passive_deletes=True
    )


class Bed(Timestamps, Base):
    __tablename__ = "beds"
    __table_args__ = (CheckConstraint("width > 0 AND height > 0", name="positive_size"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    garden: Mapped[Garden] = relationship(back_populates="beds")
    plantings: Mapped[list["Planting"]] = relationship(
        back_populates="bed", cascade="all, delete-orphan", passive_deletes=True
    )


class PlanStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"


class Plan(Timestamps, Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("garden_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id", ondelete="CASCADE"))
    year: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[PlanStatus] = mapped_column(
        str_enum(PlanStatus, "planstatus"), default=PlanStatus.DRAFT
    )
    garden: Mapped[Garden] = relationship(back_populates="plans")
    crops: Mapped[list["PlannedCrop"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlannedCrop.id",
    )
    placements: Mapped[list["PlanPlacement"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanPlacement.id",
    )


class Planting(Timestamps, Base):
    __tablename__ = "plantings"
    __table_args__ = (
        window_order(),
        CheckConstraint("coverage > 0 AND coverage <= 1", name="coverage_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    start_month: Mapped[date] = mapped_column(Date)
    end_month: Mapped[date] = mapped_column(Date)
    coverage: Mapped[float] = mapped_column(Float, default=1.0)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"), index=True
    )
    bed: Mapped[Bed] = relationship(back_populates="plantings")


class PlannedCrop(Base):
    __tablename__ = "planned_crops"
    __table_args__ = (
        UniqueConstraint("plan_id", "crop_id"),
        CheckConstraint("quantity >= 1", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    plan: Mapped[Plan] = relationship(back_populates="crops")


class PlacementSource(StrEnum):
    MANUAL = "manual"
    SUGGESTED = "suggested"


class PlanPlacement(Timestamps, Base):
    __tablename__ = "plan_placements"
    __table_args__ = (window_order(),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    start_month: Mapped[date] = mapped_column(Date)
    end_month: Mapped[date] = mapped_column(Date)
    locked: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[PlacementSource] = mapped_column(
        str_enum(PlacementSource, "placementsource"), default=PlacementSource.MANUAL
    )
    plan: Mapped[Plan] = relationship(back_populates="placements")
