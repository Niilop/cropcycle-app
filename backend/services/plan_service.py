from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.database import (
    Bed,
    Garden,
    PlacementSource,
    Plan,
    PlannedCrop,
    PlanPlacement,
    PlanStatus,
    Planting,
)
from backend.models.schemas import (
    AssessmentResponse,
    PlacementWrite,
    PlanCreate,
    PlanDetailResponse,
    PlannedCropResponse,
    PlannedCropWrite,
    PlanUpdate,
)
from backend.services import layout_service
from backend.services.errors import ConflictError, InvalidReferenceError, NotFoundError
from backend.services.garden_service import get_crop, get_garden, resolve_window
from backend.services.layout import Unplaced
from backend.services.windows import touches_year

# Plans


def list_plans(db: Session, garden_id: int) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.garden_id == garden_id).order_by(Plan.year)))


def get_plan(db: Session, plan_id: int, user_id: int) -> Plan:
    plan = db.scalar(select(Plan).join(Garden).where(Plan.id == plan_id, Garden.user_id == user_id))
    if plan is None:
        raise NotFoundError("Plan not found")
    return plan


def plan_detail(db: Session, plan: Plan) -> PlanDetailResponse:
    """The plan with requested/placed counts and a fresh assessment of each placement."""
    placed = Counter(placement.crop_id for placement in plan.placements)
    detail = PlanDetailResponse.model_validate(plan)
    assessments = layout_service.assess_plan(db, plan)
    for placement in detail.placements:
        assessment = assessments.get(placement.id)
        if assessment is not None:
            placement.assessment = AssessmentResponse(
                score=assessment.score,
                band=assessment.band.value,
                reasons=[reason.value for reason in assessment.reasons],
            )
    detail.crops = [
        PlannedCropResponse(
            id=crop.id, crop_id=crop.crop_id, quantity=crop.quantity, placed=placed[crop.crop_id]
        )
        for crop in plan.crops
    ]
    return detail


def create_plan(db: Session, user_id: int, body: PlanCreate) -> Plan:
    try:
        garden = get_garden(db, body.garden_id, user_id)
    except NotFoundError as exc:
        raise InvalidReferenceError("Unknown garden") from exc
    plan = Plan(garden_id=garden.id, year=body.year, name=body.name or str(body.year))
    db.add(plan)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This garden already has a plan for that year") from exc
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan: Plan, body: PlanUpdate) -> Plan:
    plan.name = body.name
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan: Plan) -> None:
    """Delete the plan; history written by completing it stays (the FK sets plan_id to NULL)."""
    db.delete(plan)
    db.commit()


def require_draft(plan: Plan) -> None:
    if plan.status != PlanStatus.DRAFT:
        raise ConflictError("The plan is completed; reopen it to make changes")


def complete_plan(db: Session, plan: Plan) -> Plan:
    """Mark the plan completed and replace the history it previously wrote with its placements."""
    db.execute(delete(Planting).where(Planting.plan_id == plan.id))
    for placement in plan.placements:
        db.add(
            Planting(
                bed_id=placement.bed_id,
                crop_id=placement.crop_id,
                year=plan.year,
                start_month=placement.start_month,
                end_month=placement.end_month,
                plan_id=plan.id,
            )
        )
    plan.status = PlanStatus.COMPLETED
    db.commit()
    db.refresh(plan)
    return plan


def reopen_plan(db: Session, plan: Plan) -> Plan:
    plan.status = PlanStatus.DRAFT
    db.commit()
    db.refresh(plan)
    return plan


# Requested crops


def upsert_planned_crop(db: Session, plan: Plan, body: PlannedCropWrite) -> tuple[Plan, bool]:
    """Set the requested quantity for a crop. Returns the plan and whether the crop was added."""
    require_draft(plan)
    get_crop(db, body.crop_id)
    existing = next((crop for crop in plan.crops if crop.crop_id == body.crop_id), None)
    if existing is None:
        plan.crops.append(PlannedCrop(crop_id=body.crop_id, quantity=body.quantity))
    else:
        existing.quantity = body.quantity
    db.commit()
    db.refresh(plan)
    return plan, existing is None


def remove_planned_crop(db: Session, plan: Plan, crop_id: int) -> None:
    """Remove a requested crop and its placements from the plan."""
    require_draft(plan)
    existing = next((crop for crop in plan.crops if crop.crop_id == crop_id), None)
    if existing is None:
        raise NotFoundError("Crop is not in this plan")
    plan.crops.remove(existing)
    for placement in [p for p in plan.placements if p.crop_id == crop_id]:
        plan.placements.remove(placement)
    db.commit()


# Placements


def get_placement(db: Session, placement_id: int, user_id: int) -> PlanPlacement:
    placement = db.scalar(
        select(PlanPlacement)
        .join(Plan)
        .join(Garden)
        .where(PlanPlacement.id == placement_id, Garden.user_id == user_id)
    )
    if placement is None:
        raise NotFoundError("Placement not found")
    return placement


def apply_placement(
    db: Session, plan: Plan, placement: PlanPlacement, body: PlacementWrite
) -> None:
    bed = db.get(Bed, body.bed_id)
    if bed is None or bed.garden_id != plan.garden_id:
        raise InvalidReferenceError("Unknown bed")
    if bed.archived_at is not None:
        raise ConflictError("The bed is archived; restore it before planning crops in it")
    crop = get_crop(db, body.crop_id)
    start, end = resolve_window(crop, plan.year, body.start_month, body.end_month)
    if not touches_year(start, end, plan.year):
        raise InvalidReferenceError("The window must include part of the plan year")
    placement.bed_id = bed.id
    placement.crop_id = crop.id
    placement.start_month = start
    placement.end_month = end
    placement.locked = body.locked
    # Any user edit makes the placement the user's own choice (D008).
    placement.source = PlacementSource.MANUAL


def create_placement(db: Session, plan: Plan, body: PlacementWrite) -> PlanPlacement:
    require_draft(plan)
    placement = PlanPlacement(plan_id=plan.id)
    apply_placement(db, plan, placement, body)
    db.add(placement)
    db.commit()
    db.refresh(placement)
    return placement


def update_placement(db: Session, placement: PlanPlacement, body: PlacementWrite) -> PlanPlacement:
    require_draft(placement.plan)
    apply_placement(db, placement.plan, placement, body)
    db.commit()
    db.refresh(placement)
    return placement


def delete_placement(db: Session, placement: PlanPlacement) -> None:
    require_draft(placement.plan)
    db.delete(placement)
    db.commit()


def fill_remaining(db: Session, plan: Plan) -> list[Unplaced]:
    """Replace unlocked suggestions with a new layout for all unplaced requested crops.

    Manual and locked placements are never changed (D008).
    """
    require_draft(plan)
    for placement in [
        p for p in plan.placements if p.source == PlacementSource.SUGGESTED and not p.locked
    ]:
        plan.placements.remove(placement)
    db.flush()
    placed = Counter(placement.crop_id for placement in plan.placements)
    demand = {
        requested.crop_id: requested.quantity - placed[requested.crop_id]
        for requested in plan.crops
        if requested.quantity > placed[requested.crop_id]
    }
    result = layout_service.generate(db, plan, demand)
    for suggestion in result.suggestions:
        plan.placements.append(
            PlanPlacement(
                bed_id=suggestion.bed_id,
                crop_id=suggestion.crop_id,
                start_month=layout_service.to_date(suggestion.window.start),
                end_month=layout_service.to_date(suggestion.window.end),
                locked=False,
                source=PlacementSource.SUGGESTED,
            )
        )
    db.commit()
    db.refresh(plan)
    return result.unplaced
