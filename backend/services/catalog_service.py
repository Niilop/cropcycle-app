from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import CompanionRule, Crop, CropFamily, RotationRule


def list_families(db: Session) -> list[CropFamily]:
    return list(db.scalars(select(CropFamily).order_by(CropFamily.id)))


def list_crops(db: Session) -> list[Crop]:
    return list(db.scalars(select(Crop).order_by(Crop.id)))


def list_rotation_rules(db: Session) -> list[RotationRule]:
    return list(db.scalars(select(RotationRule).order_by(RotationRule.id)))


def list_companion_rules(db: Session) -> list[CompanionRule]:
    return list(db.scalars(select(CompanionRule).order_by(CompanionRule.id)))
