"""Suitability of a crop in a bed for a window, as a 0–100 score, a band and reason codes."""

from collections import defaultdict
from collections.abc import Iterable

from backend.services.layout.model import (
    Assessment,
    Band,
    Catalog,
    Compat,
    Garden,
    Occupant,
    Reason,
    Rule,
    Window,
)

# Share of the base score; neighbours adjust it afterwards.
CROP_ROTATION_WEIGHT = 0.35
FAMILY_ROTATION_WEIGHT = 0.45
TIMING_WEIGHT = 0.20
POSITIVE_NEIGHBOR_POINTS = 5.0
NEGATIVE_NEIGHBOR_POINTS = 10.0
NEIGHBOR_BONUS_CAP = 10.0
NEIGHBOR_PENALTY_CAP = 20.0
BAND_THRESHOLDS = ((80, Band.VERY_SUITABLE), (60, Band.SUITABLE), (40, Band.POSSIBLE))


def gap_score(gap: int | None, rule: Rule) -> float:
    """1.0 when the preferred gap is met, falling to 0.0 for a repeat after one year or less."""
    if gap is None or gap >= rule.gap_years:
        return 1.0
    base = 0.0 if rule.gap_years <= 1 else max(0.0, (gap - 1) / (rule.gap_years - 1))
    return max(0.0, 1.0 - rule.weight * (1.0 - base))


class Scorer:
    """Scores placements against the garden background plus the current plan occupants."""

    def __init__(self, catalog: Catalog, garden: Garden) -> None:
        self.catalog = catalog
        self.garden = garden

    def index(self, occupants: Iterable[Occupant]) -> dict[int, list[Occupant]]:
        by_bed: dict[int, list[Occupant]] = defaultdict(list)
        for occupant in [*self.garden.background, *occupants]:
            by_bed[occupant.bed_id].append(occupant)
        return by_bed

    def evaluate(
        self,
        crop_id: int,
        bed_id: int,
        window: Window,
        by_bed: dict[int, list[Occupant]],
        exclude: str | None = None,
    ) -> tuple[float, Band, tuple[Reason, ...]]:
        catalog, year = self.catalog, self.garden.year
        crop = catalog.crops[crop_id]
        here = [o for o in by_bed.get(bed_id, ()) if o.key != exclude]
        reasons: list[Reason] = []

        # Rotation: years since the same crop, and the same family, used this bed.
        past = [o for o in here if o.year <= year]
        same_crop = [year - o.year for o in past if o.crop_id == crop_id]
        same_family = [
            year - o.year for o in past if catalog.crops[o.crop_id].family_id == crop.family_id
        ]
        crop_rule, family_rule = catalog.crop_rule(crop_id), catalog.family_rule(crop.family_id)
        crop_gap = min(same_crop, default=None)
        family_gap = min(same_family, default=None)
        crop_score = gap_score(crop_gap, crop_rule)
        family_score = gap_score(family_gap, family_rule)
        if not past:
            reasons.append(Reason.NO_HISTORY)
        elif crop_gap is not None and crop_gap < crop_rule.gap_years:
            reasons.append(Reason.SAME_CROP_RECENT)
        elif family_gap is not None and family_gap < family_rule.gap_years:
            reasons.append(Reason.SAME_FAMILY_RECENT)
        else:
            reasons.append(Reason.GOOD_ROTATION_INTERVAL)

        # Neighbours in adjacent beds whose seasons overlap this one.
        adjustment, positive, negative = 0.0, False, False
        for neighbor_bed in sorted(self.garden.neighbors.get(bed_id, ())):
            for other in by_bed.get(neighbor_bed, ()):
                if other.key == exclude or not window.shared_months(other.window):
                    continue
                relation = catalog.companion(crop_id, other.crop_id)
                if relation is None:
                    continue
                compat, weight = relation
                if compat == Compat.POSITIVE:
                    adjustment += POSITIVE_NEIGHBOR_POINTS * weight
                    positive = True
                elif compat == Compat.NEGATIVE:
                    adjustment -= NEGATIVE_NEIGHBOR_POINTS * weight
                    negative = True
        adjustment = max(-NEIGHBOR_PENALTY_CAP, min(NEIGHBOR_BONUS_CAP, adjustment))
        if positive:
            reasons.append(Reason.COMPATIBLE_NEIGHBOR)
        if negative:
            reasons.append(Reason.LESS_COMPATIBLE_NEIGHBOR)

        # Timing: other crops in this bed during the window.
        extra = max((window.extra_overlap(o.window) for o in here), default=0)
        timing_score = 1.0 if extra == 0 else 0.5 if extra == 1 else 0.0
        reasons.append(
            Reason.FITS_SEASON
            if extra == 0
            else Reason.LIMITED_SEASON
            if extra == 1
            else Reason.TIMING_CONFLICT
        )

        base = (
            CROP_ROTATION_WEIGHT * crop_score
            + FAMILY_ROTATION_WEIGHT * family_score
            + TIMING_WEIGHT * timing_score
        )
        score = max(0.0, min(100.0, 100 * base + adjustment))
        if extra >= 2:
            band = Band.NO_FREE_SEASON
        else:
            band = next((b for limit, b in BAND_THRESHOLDS if score >= limit), None)
            band = band or Band.SOME_CONSIDERATIONS
        return score, band, tuple(reasons)

    def assess(
        self,
        crop_id: int,
        bed_id: int,
        window: Window,
        by_bed: dict[int, list[Occupant]],
        exclude: str | None = None,
    ) -> Assessment:
        score, band, reasons = self.evaluate(crop_id, bed_id, window, by_bed, exclude)
        return Assessment(score=round(score), band=band, reasons=reasons)
