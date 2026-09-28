from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from backend.api.dependencies import (
    WRITE_LIMIT,
    owned_bed,
    owned_garden,
    owned_planting,
)
from backend.api.endpoints.auth import get_current_user
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.models.database import Bed, Garden, Planting, User
from backend.models.schemas import (
    BedResponse,
    BedWrite,
    GardenDetailResponse,
    GardenResponse,
    GardenWrite,
    PlantingResponse,
    PlantingWrite,
    Year,
)
from backend.services import garden_service

router = APIRouter(tags=["Gardens"])


@router.get("/gardens", response_model=list[GardenResponse])
def list_gardens(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Garden]:
    return garden_service.list_gardens(db, user.id)


@router.post("/gardens", response_model=GardenResponse, status_code=201)
@limiter.limit(WRITE_LIMIT)
def create_garden(
    request: Request,
    body: GardenWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Garden:
    return garden_service.create_garden(db, user.id, body)


@router.get("/gardens/{garden_id}", response_model=GardenDetailResponse)
def read_garden(
    include_archived: bool = False,
    garden: Garden = Depends(owned_garden),
    db: Session = Depends(get_db),
) -> GardenDetailResponse:
    beds = garden_service.list_beds(db, garden.id, include_archived)
    return GardenDetailResponse(
        **GardenResponse.model_validate(garden).model_dump(),
        beds=[BedResponse.model_validate(bed) for bed in beds],
    )


@router.put("/gardens/{garden_id}", response_model=GardenResponse)
@limiter.limit(WRITE_LIMIT)
def update_garden(
    request: Request,
    body: GardenWrite,
    garden: Garden = Depends(owned_garden),
    db: Session = Depends(get_db),
) -> Garden:
    return garden_service.update_garden(db, garden, body)


@router.delete("/gardens/{garden_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def delete_garden(
    request: Request, garden: Garden = Depends(owned_garden), db: Session = Depends(get_db)
) -> Response:
    garden_service.delete_garden(db, garden)
    return Response(status_code=204)


@router.post("/gardens/{garden_id}/beds", response_model=BedResponse, status_code=201)
@limiter.limit(WRITE_LIMIT)
def create_bed(
    request: Request,
    body: BedWrite,
    garden: Garden = Depends(owned_garden),
    db: Session = Depends(get_db),
) -> Bed:
    return garden_service.create_bed(db, garden, body)


@router.put("/beds/{bed_id}", response_model=BedResponse)
@limiter.limit(WRITE_LIMIT)
def update_bed(
    request: Request, body: BedWrite, bed: Bed = Depends(owned_bed), db: Session = Depends(get_db)
) -> Bed:
    return garden_service.update_bed(db, bed, body)


@router.delete("/beds/{bed_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def archive_bed(
    request: Request, bed: Bed = Depends(owned_bed), db: Session = Depends(get_db)
) -> Response:
    garden_service.archive_bed(db, bed)
    return Response(status_code=204)


@router.post("/beds/{bed_id}/restore", response_model=BedResponse)
@limiter.limit(WRITE_LIMIT)
def restore_bed(
    request: Request, bed: Bed = Depends(owned_bed), db: Session = Depends(get_db)
) -> Bed:
    return garden_service.restore_bed(db, bed)


@router.get("/gardens/{garden_id}/plantings", response_model=list[PlantingResponse])
def list_garden_plantings(
    year_from: Year | None = Query(default=None),
    year_to: Year | None = Query(default=None),
    garden: Garden = Depends(owned_garden),
    db: Session = Depends(get_db),
) -> list[Planting]:
    return garden_service.list_garden_plantings(db, garden.id, year_from, year_to)


@router.get("/beds/{bed_id}/plantings", response_model=list[PlantingResponse])
def list_bed_plantings(
    bed: Bed = Depends(owned_bed), db: Session = Depends(get_db)
) -> list[Planting]:
    return garden_service.list_bed_plantings(db, bed.id)


@router.post("/beds/{bed_id}/plantings", response_model=PlantingResponse, status_code=201)
@limiter.limit(WRITE_LIMIT)
def create_planting(
    request: Request,
    body: PlantingWrite,
    bed: Bed = Depends(owned_bed),
    db: Session = Depends(get_db),
) -> Planting:
    return garden_service.create_planting(db, bed, body)


@router.put("/plantings/{planting_id}", response_model=PlantingResponse)
@limiter.limit(WRITE_LIMIT)
def update_planting(
    request: Request,
    body: PlantingWrite,
    planting: Planting = Depends(owned_planting),
    db: Session = Depends(get_db),
) -> Planting:
    return garden_service.update_planting(db, planting, body)


@router.delete("/plantings/{planting_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
def delete_planting(
    request: Request, planting: Planting = Depends(owned_planting), db: Session = Depends(get_db)
) -> Response:
    garden_service.delete_planting(db, planting)
    return Response(status_code=204)
