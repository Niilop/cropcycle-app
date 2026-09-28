from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import Bed, Crop, Garden, Planting, utc_now
from backend.models.schemas import BedWrite, GardenWrite, PlantingWrite
from backend.services.errors import InvalidReferenceError, NotFoundError
from backend.services.windows import default_window

# Gardens


def list_gardens(db: Session, user_id: int) -> list[Garden]:
    return list(db.scalars(select(Garden).where(Garden.user_id == user_id).order_by(Garden.id)))


def get_garden(db: Session, garden_id: int, user_id: int) -> Garden:
    garden = db.scalar(select(Garden).where(Garden.id == garden_id, Garden.user_id == user_id))
    if garden is None:
        raise NotFoundError("Garden not found")
    return garden


def create_garden(db: Session, user_id: int, body: GardenWrite) -> Garden:
    garden = Garden(user_id=user_id, name=body.name)
    db.add(garden)
    db.commit()
    db.refresh(garden)
    return garden


def update_garden(db: Session, garden: Garden, body: GardenWrite) -> Garden:
    garden.name = body.name
    db.commit()
    db.refresh(garden)
    return garden


def delete_garden(db: Session, garden: Garden) -> None:
    db.delete(garden)
    db.commit()


# Beds


def list_beds(db: Session, garden_id: int, include_archived: bool = False) -> list[Bed]:
    query = select(Bed).where(Bed.garden_id == garden_id).order_by(Bed.id)
    if not include_archived:
        query = query.where(Bed.archived_at.is_(None))
    return list(db.scalars(query))


def get_bed(db: Session, bed_id: int, user_id: int) -> Bed:
    bed = db.scalar(select(Bed).join(Garden).where(Bed.id == bed_id, Garden.user_id == user_id))
    if bed is None:
        raise NotFoundError("Bed not found")
    return bed


def create_bed(db: Session, garden: Garden, body: BedWrite) -> Bed:
    bed = Bed(garden_id=garden.id, **body.model_dump())
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return bed


def update_bed(db: Session, bed: Bed, body: BedWrite) -> Bed:
    for field, value in body.model_dump().items():
        setattr(bed, field, value)
    db.commit()
    db.refresh(bed)
    return bed


def archive_bed(db: Session, bed: Bed) -> None:
    """Hide the bed from layouts while keeping its history (D011)."""
    if bed.archived_at is None:
        bed.archived_at = utc_now()
        db.commit()


def restore_bed(db: Session, bed: Bed) -> Bed:
    bed.archived_at = None
    db.commit()
    db.refresh(bed)
    return bed


# Plantings


def get_crop(db: Session, crop_id: int) -> Crop:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise InvalidReferenceError("Unknown crop")
    return crop


def resolve_window(
    crop: Crop, year: int, start: date | None, end: date | None
) -> tuple[date, date]:
    if start is not None and end is not None:
        return start, end
    return default_window(crop, year)


def list_bed_plantings(db: Session, bed_id: int) -> list[Planting]:
    return list(
        db.scalars(
            select(Planting)
            .where(Planting.bed_id == bed_id)
            .order_by(Planting.start_month.desc(), Planting.id.desc())
        )
    )


def list_garden_plantings(
    db: Session, garden_id: int, year_from: int | None, year_to: int | None
) -> list[Planting]:
    query = select(Planting).join(Bed).where(Bed.garden_id == garden_id)
    if year_from is not None:
        query = query.where(Planting.year >= year_from)
    if year_to is not None:
        query = query.where(Planting.year <= year_to)
    return list(db.scalars(query.order_by(Planting.start_month.desc(), Planting.id.desc())))


def get_planting(db: Session, planting_id: int, user_id: int) -> Planting:
    planting = db.scalar(
        select(Planting)
        .join(Bed)
        .join(Garden)
        .where(Planting.id == planting_id, Garden.user_id == user_id)
    )
    if planting is None:
        raise NotFoundError("Planting not found")
    return planting


def create_planting(db: Session, bed: Bed, body: PlantingWrite) -> Planting:
    crop = get_crop(db, body.crop_id)
    start, end = resolve_window(crop, body.year, body.start_month, body.end_month)
    planting = Planting(
        bed_id=bed.id, crop_id=crop.id, year=body.year, start_month=start, end_month=end
    )
    db.add(planting)
    db.commit()
    db.refresh(planting)
    return planting


def update_planting(db: Session, planting: Planting, body: PlantingWrite) -> Planting:
    crop = get_crop(db, body.crop_id)
    planting.crop_id = crop.id
    planting.year = body.year
    planting.start_month, planting.end_month = resolve_window(
        crop, body.year, body.start_month, body.end_month
    )
    db.commit()
    db.refresh(planting)
    return planting


def delete_planting(db: Session, planting: Planting) -> None:
    db.delete(planting)
    db.commit()
