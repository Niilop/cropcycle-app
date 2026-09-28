"""Owner-scoped lookups shared by the domain routers. Foreign and missing records are 404."""

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from backend.api.endpoints.auth import get_current_user
from backend.core.database import get_db
from backend.models.database import Bed, Garden, Plan, PlanPlacement, Planting, User
from backend.services import garden_service, plan_service

WRITE_LIMIT = "120/minute"


def owned_garden(
    garden_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Garden:
    return garden_service.get_garden(db, garden_id, user.id)


def owned_bed(
    bed_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bed:
    return garden_service.get_bed(db, bed_id, user.id)


def owned_planting(
    planting_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Planting:
    return garden_service.get_planting(db, planting_id, user.id)


def owned_plan(
    plan_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Plan:
    return plan_service.get_plan(db, plan_id, user.id)


def owned_placement(
    placement_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanPlacement:
    return plan_service.get_placement(db, placement_id, user.id)
