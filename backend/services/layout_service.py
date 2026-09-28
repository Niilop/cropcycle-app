"""Adapts stored gardens and plans to the pure layout module and applies its results."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import (
    Bed,
    CompanionRule,
    Crop,
    Plan,
    PlanPlacement,
    PlanStatus,
    Planting,
    RotationRule,
)
from backend.services import layout
from backend.services.garden_service import get_crop
from backend.services.windows import default_window

# History older than this cannot affect rotation scores.
HISTORY_YEARS = 10


def to_window(start: date, end: date) -> layout.Window:
    return layout.Window(
        layout.month_index(start.year, start.month), layout.month_index(end.year, end.month)
    )


def to_date(index: int) -> date:
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def placement_key(placement_id: int) -> str:
    return f"placement:{placement_id}"


@dataclass
class PlanContext:
    scorer: layout.Scorer
    placements: list[PlanPlacement]
    active_bed_ids: set[int]

    def occupants(self, placements: list[PlanPlacement]) -> list[layout.Occupant]:
        year = self.scorer.garden.year
        return [
            layout.Occupant(
                placement_key(p.id),
                p.bed_id,
                p.crop_id,
                to_window(p.start_month, p.end_month),
                year,
            )
            for p in placements
            if p.bed_id in self.active_bed_ids
        ]


def load_catalog(db: Session, year: int) -> layout.Catalog:
    crops = {
        crop.id: layout.CropInfo(crop.id, crop.family_id, to_window(*default_window(crop, year)))
        for crop in db.scalars(select(Crop))
    }
    catalog = layout.Catalog(crops=crops)
    for rule in db.scalars(select(RotationRule)):
        target = catalog.crop_rules if rule.crop_id is not None else catalog.family_rules
        target[rule.crop_id or rule.family_id] = layout.Rule(rule.preferred_gap_years, rule.weight)
    for rule in db.scalars(select(CompanionRule)):
        catalog.companions[(rule.crop_a_id, rule.crop_b_id)] = (
            layout.Compat(rule.compatibility.value),
            rule.weight,
        )
    return catalog


def load_context(db: Session, plan: Plan) -> PlanContext:
    beds = list(
        db.scalars(
            select(Bed)
            .where(Bed.garden_id == plan.garden_id, Bed.archived_at.is_(None))
            .order_by(Bed.id)
        )
    )
    bed_ids = {bed.id for bed in beds}
    background = [
        layout.Occupant(
            f"planting:{p.id}", p.bed_id, p.crop_id, to_window(p.start_month, p.end_month), p.year
        )
        for p in db.scalars(
            select(Planting).where(
                Planting.bed_id.in_(bed_ids),
                Planting.year >= plan.year - HISTORY_YEARS,
                # A completed plan's own history duplicates its placements.
                (Planting.plan_id.is_(None)) | (Planting.plan_id != plan.id),
            )
        )
    ]
    # Draft plans for adjacent years occupy beds too (garlic planted this autumn for next
    # year); completed plans are already represented by the history they wrote.
    for other in db.scalars(
        select(Plan).where(
            Plan.garden_id == plan.garden_id,
            Plan.year.in_((plan.year - 1, plan.year + 1)),
            Plan.status == PlanStatus.DRAFT,
        )
    ):
        background.extend(
            layout.Occupant(
                f"other-plan:{p.id}",
                p.bed_id,
                p.crop_id,
                to_window(p.start_month, p.end_month),
                other.year,
            )
            for p in other.placements
            if p.bed_id in bed_ids
        )
    garden = layout.Garden(
        year=plan.year,
        beds=[layout.BedShape(b.id, b.x, b.y, b.width, b.height) for b in beds],
        background=background,
    )
    scorer = layout.Scorer(load_catalog(db, plan.year), garden)
    return PlanContext(scorer, list(plan.placements), bed_ids)


def assess_plan(db: Session, plan: Plan) -> dict[int, layout.Assessment]:
    """Current assessment of every placement in an active bed, keyed by placement id."""
    context = load_context(db, plan)
    by_bed = context.scorer.index(context.occupants(context.placements))
    return {
        p.id: context.scorer.assess(
            p.crop_id, p.bed_id, to_window(p.start_month, p.end_month), by_bed, placement_key(p.id)
        )
        for p in context.placements
        if p.bed_id in context.active_bed_ids
    }


@dataclass
class BedSuitability:
    bed_id: int
    start_month: date
    end_month: date
    assessment: layout.Assessment


def suitability(db: Session, plan: Plan, crop_id: int) -> list[BedSuitability]:
    """How well a new placement of the crop would fit each active bed, given the plan so far."""
    crop = get_crop(db, crop_id)
    context = load_context(db, plan)
    by_bed = context.scorer.index(context.occupants(context.placements))
    start, end = default_window(crop, plan.year)
    window = to_window(start, end)
    return [
        BedSuitability(bed.id, start, end, context.scorer.assess(crop.id, bed.id, window, by_bed))
        for bed in context.scorer.garden.beds
    ]


def generate(db: Session, plan: Plan, demand: dict[int, int]) -> layout.LayoutResult:
    """Run the layout engine for `demand` around the plan's current placements."""
    context = load_context(db, plan)
    return layout.generate_layout(
        context.scorer.catalog,
        context.scorer.garden,
        context.occupants(list(plan.placements)),
        demand,
    )
