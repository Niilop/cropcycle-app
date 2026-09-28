from fastapi import APIRouter, Depends, Path, Query, Request, Response
from sqlalchemy.orm import Session

from backend.api.dependencies import WRITE_LIMIT, owned_placement, owned_plan
from backend.api.endpoints.auth import get_current_user
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.models.database import Plan, PlanPlacement, User
from backend.models.schemas import (
    PlacementResponse,
    PlacementWrite,
    PlanCreate,
    PlanDetailResponse,
    PlannedCropWrite,
    PlanResponse,
    PlanUpdate,
)
from backend.services import garden_service, plan_service

router = APIRouter(tags=["Plans"])


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    garden_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Plan]:
    garden = garden_service.get_garden(db, garden_id, user.id)
    return plan_service.list_plans(db, garden.id)


@router.post("/plans", response_model=PlanDetailResponse, status_code=201)
@limiter.limit(WRITE_LIMIT)
def create_plan(
    request: Request,
    body: PlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanDetailResponse:
    return plan_service.plan_detail(plan_service.create_plan(db, user.id, body))


@router.get("/plans/{plan_id}", response_model=PlanDetailResponse)
def read_plan(plan: Plan = Depends(owned_plan)) -> PlanDetailResponse:
    return plan_service.plan_detail(plan)


@router.put("/plans/{plan_id}", response_model=PlanDetailResponse)
@limiter.limit(WRITE_LIMIT)
def update_plan(
    request: Request,
    body: PlanUpdate,
    plan: Plan = Depends(owned_plan),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    return plan_service.plan_detail(plan_service.update_plan(db, plan, body))


@router.delete("/plans/{plan_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def delete_plan(
    request: Request, plan: Plan = Depends(owned_plan), db: Session = Depends(get_db)
) -> Response:
    plan_service.delete_plan(db, plan)
    return Response(status_code=204)


@router.post("/plans/{plan_id}/complete", response_model=PlanDetailResponse)
@limiter.limit(WRITE_LIMIT)
def complete_plan(
    request: Request, plan: Plan = Depends(owned_plan), db: Session = Depends(get_db)
) -> PlanDetailResponse:
    return plan_service.plan_detail(plan_service.complete_plan(db, plan))


@router.post("/plans/{plan_id}/reopen", response_model=PlanDetailResponse)
@limiter.limit(WRITE_LIMIT)
def reopen_plan(
    request: Request, plan: Plan = Depends(owned_plan), db: Session = Depends(get_db)
) -> PlanDetailResponse:
    return plan_service.plan_detail(plan_service.reopen_plan(db, plan))


@router.post("/plans/{plan_id}/crops", response_model=PlanDetailResponse)
@limiter.limit(WRITE_LIMIT)
def set_planned_crop(
    request: Request,
    response: Response,
    body: PlannedCropWrite,
    plan: Plan = Depends(owned_plan),
    db: Session = Depends(get_db),
) -> PlanDetailResponse:
    """Add a crop to the plan, or change its quantity if it is already requested."""
    plan, created = plan_service.upsert_planned_crop(db, plan, body)
    response.status_code = 201 if created else 200
    return plan_service.plan_detail(plan)


@router.delete("/plans/{plan_id}/crops/{crop_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def remove_planned_crop(
    request: Request,
    crop_id: int = Path(gt=0),
    plan: Plan = Depends(owned_plan),
    db: Session = Depends(get_db),
) -> Response:
    plan_service.remove_planned_crop(db, plan, crop_id)
    return Response(status_code=204)


@router.post("/plans/{plan_id}/placements", response_model=PlacementResponse, status_code=201)
@limiter.limit(WRITE_LIMIT)
def create_placement(
    request: Request,
    body: PlacementWrite,
    plan: Plan = Depends(owned_plan),
    db: Session = Depends(get_db),
) -> PlanPlacement:
    return plan_service.create_placement(db, plan, body)


@router.put("/plan-placements/{placement_id}", response_model=PlacementResponse)
@limiter.limit(WRITE_LIMIT)
def update_placement(
    request: Request,
    body: PlacementWrite,
    placement: PlanPlacement = Depends(owned_placement),
    db: Session = Depends(get_db),
) -> PlanPlacement:
    return plan_service.update_placement(db, placement, body)


@router.delete("/plan-placements/{placement_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def delete_placement(
    request: Request,
    placement: PlanPlacement = Depends(owned_placement),
    db: Session = Depends(get_db),
) -> Response:
    plan_service.delete_placement(db, placement)
    return Response(status_code=204)
