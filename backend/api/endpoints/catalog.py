from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.endpoints.auth import get_current_user
from backend.core.database import get_db
from backend.models.database import CompanionRule, Crop, CropFamily, RotationRule
from backend.models.schemas import (
    CompanionRuleResponse,
    CropFamilyResponse,
    CropResponse,
    RotationRuleResponse,
)
from backend.services import catalog_service

router = APIRouter(tags=["Catalogue"], dependencies=[Depends(get_current_user)])


@router.get("/crop-families", response_model=list[CropFamilyResponse])
def list_families(db: Session = Depends(get_db)) -> list[CropFamily]:
    return catalog_service.list_families(db)


@router.get("/crops", response_model=list[CropResponse])
def list_crops(db: Session = Depends(get_db)) -> list[Crop]:
    return catalog_service.list_crops(db)


@router.get("/rotation-rules", response_model=list[RotationRuleResponse])
def list_rotation_rules(db: Session = Depends(get_db)) -> list[RotationRule]:
    return catalog_service.list_rotation_rules(db)


@router.get("/companion-rules", response_model=list[CompanionRuleResponse])
def list_companion_rules(db: Session = Depends(get_db)) -> list[CompanionRule]:
    return catalog_service.list_companion_rules(db)
