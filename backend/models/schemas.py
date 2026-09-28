import re
from datetime import date, datetime
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    WithJsonSchema,
    model_validator,
)

from backend.models.database import Compatibility, PlacementSource, PlanStatus

YEAR_MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
MIN_YEAR, MAX_YEAR = 1900, 2200
MAX_WINDOW_MONTHS = 24


def parse_year_month(value: object) -> object:
    if isinstance(value, str):
        if not re.fullmatch(YEAR_MONTH_PATTERN, value):
            raise ValueError("Expected a year and month as YYYY-MM")
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    return value


def check_year_month(value: date) -> date:
    if value.day != 1:
        raise ValueError("Expected the first day of a month")
    if not MIN_YEAR <= value.year <= MAX_YEAR:
        raise ValueError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")
    return value


# First-of-month date, exchanged as "YYYY-MM" (D012).
YearMonth = Annotated[
    date,
    BeforeValidator(parse_year_month),
    AfterValidator(check_year_month),
    PlainSerializer(lambda value: f"{value.year:04d}-{value.month:02d}", return_type=str),
    WithJsonSchema({"type": "string", "pattern": YEAR_MONTH_PATTERN, "examples": ["2026-05"]}),
]
Year = Annotated[int, Field(ge=MIN_YEAR, le=MAX_YEAR)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Metres = Annotated[float, Field(ge=-1000, le=1000, allow_inf_nan=False)]
Size = Annotated[float, Field(gt=0, le=1000, allow_inf_nan=False)]
LocalizedNames = dict[str, str]


def months_between(start: date, end: date) -> int:
    """Number of months covered by an inclusive window."""
    return (end.year - start.year) * 12 + end.month - start.month + 1


class WriteModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OptionalWindow(WriteModel):
    """A window that falls back to the crop's default for the relevant year when omitted."""

    start_month: YearMonth | None = None
    end_month: YearMonth | None = None

    @model_validator(mode="after")
    def check_window(self) -> Self:
        if (self.start_month is None) != (self.end_month is None):
            raise ValueError("Provide both start_month and end_month, or neither")
        if self.start_month is not None and self.end_month is not None:
            if self.start_month > self.end_month:
                raise ValueError("start_month must not be after end_month")
            if months_between(self.start_month, self.end_month) > MAX_WINDOW_MONTHS:
                raise ValueError(f"A window can span at most {MAX_WINDOW_MONTHS} months")
        return self


# Authentication


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=255)
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(ReadModel):
    id: int
    email: str
    username: str
    created_at: datetime
    settings: dict[str, Any]


# Catalogue


class CropFamilyResponse(ReadModel):
    id: int
    slug: str
    names: LocalizedNames


class CropResponse(ReadModel):
    id: int
    slug: str
    names: LocalizedNames
    family_id: int
    default_start_month: int
    default_end_month: int
    default_start_year_offset: int


class RotationRuleResponse(ReadModel):
    id: int
    crop_id: int | None
    family_id: int | None
    preferred_gap_years: int
    weight: float


class CompanionRuleResponse(ReadModel):
    id: int
    crop_a_id: int
    crop_b_id: int
    compatibility: Compatibility
    weight: float


# Gardens and beds


class GardenWrite(WriteModel):
    name: Name


class BedWrite(WriteModel):
    name: Name
    x: Metres
    y: Metres
    width: Size
    height: Size


class BedResponse(ReadModel):
    id: int
    garden_id: int
    name: str
    x: float
    y: float
    width: float
    height: float
    archived_at: datetime | None


class GardenResponse(ReadModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class GardenDetailResponse(GardenResponse):
    beds: list[BedResponse]


# Planting history


class PlantingWrite(OptionalWindow):
    crop_id: int = Field(gt=0)
    year: Year

    @model_validator(mode="after")
    def check_year_in_window(self) -> Self:
        if self.start_month is not None and self.end_month is not None:
            if not self.start_month.year <= self.year <= self.end_month.year:
                raise ValueError("year must be within the planting window")
        return self


class PlantingResponse(ReadModel):
    id: int
    bed_id: int
    crop_id: int
    year: int
    start_month: YearMonth
    end_month: YearMonth
    coverage: float
    plan_id: int | None


# Plans


class PlanCreate(WriteModel):
    garden_id: int = Field(gt=0)
    year: Year
    name: Name | None = None


class PlanUpdate(WriteModel):
    name: Name


class PlannedCropWrite(WriteModel):
    crop_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)


class PlannedCropResponse(ReadModel):
    id: int
    crop_id: int
    quantity: int
    placed: int = 0


class PlacementWrite(OptionalWindow):
    bed_id: int = Field(gt=0)
    crop_id: int = Field(gt=0)
    locked: bool = True


class PlacementResponse(ReadModel):
    id: int
    plan_id: int
    bed_id: int
    crop_id: int
    start_month: YearMonth
    end_month: YearMonth
    locked: bool
    source: PlacementSource


class PlanResponse(ReadModel):
    id: int
    garden_id: int
    year: int
    name: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime


class PlanDetailResponse(PlanResponse):
    crops: list[PlannedCropResponse]
    placements: list[PlacementResponse]
