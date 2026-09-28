"""Plain data used by scoring and layout generation. No database access (D008)."""

import math
from dataclasses import dataclass, field
from enum import StrEnum

DEFAULT_GAP_YEARS = 3
NEIGHBOR_DISTANCE_M = 1.0


def month_index(year: int, month: int) -> int:
    return year * 12 + month - 1


@dataclass(frozen=True)
class Window:
    """Inclusive range of month indices (see month_index)."""

    start: int
    end: int

    def shared_months(self, other: "Window") -> int:
        return max(0, min(self.end, other.end) - max(self.start, other.start) + 1)

    def extra_overlap(self, other: "Window") -> int:
        """Months shared beyond the one-month handover allowed between sequential crops (D012)."""
        return max(0, self.shared_months(other) - 1)


@dataclass(frozen=True)
class BedShape:
    id: int
    x: float
    y: float
    width: float
    height: float

    def distance_to(self, other: "BedShape") -> float:
        dx = max(0.0, max(self.x, other.x) - min(self.x + self.width, other.x + other.width))
        dy = max(0.0, max(self.y, other.y) - min(self.y + self.height, other.y + other.height))
        return math.hypot(dx, dy)


@dataclass(frozen=True)
class CropInfo:
    id: int
    family_id: int
    default_window: Window  # For the plan year.


@dataclass(frozen=True)
class Rule:
    gap_years: int
    weight: float


class Compat(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass(frozen=True)
class Occupant:
    """Something that uses a bed for a time: history, another year's plan, or a placement."""

    key: str
    bed_id: int
    crop_id: int
    window: Window
    year: int


@dataclass
class Catalog:
    crops: dict[int, CropInfo]
    crop_rules: dict[int, Rule] = field(default_factory=dict)
    family_rules: dict[int, Rule] = field(default_factory=dict)
    # Keyed by (smaller crop id, larger crop id).
    companions: dict[tuple[int, int], tuple[Compat, float]] = field(default_factory=dict)

    def crop_rule(self, crop_id: int) -> Rule:
        crop = self.crops[crop_id]
        return self.crop_rules.get(crop_id) or self.family_rule(crop.family_id)

    def family_rule(self, family_id: int) -> Rule:
        return self.family_rules.get(family_id) or Rule(DEFAULT_GAP_YEARS, 1.0)

    def companion(self, a: int, b: int) -> tuple[Compat, float] | None:
        return self.companions.get((min(a, b), max(a, b)))


@dataclass
class Garden:
    """Active beds and everything that occupies them, except this plan's placements."""

    year: int
    beds: list[BedShape]
    background: list[Occupant]
    neighbors: dict[int, set[int]] = field(init=False)

    def __post_init__(self) -> None:
        self.neighbors = {bed.id: set() for bed in self.beds}
        for i, a in enumerate(self.beds):
            for b in self.beds[i + 1 :]:
                if a.distance_to(b) <= NEIGHBOR_DISTANCE_M:
                    self.neighbors[a.id].add(b.id)
                    self.neighbors[b.id].add(a.id)


class Band(StrEnum):
    VERY_SUITABLE = "very_suitable"
    SUITABLE = "suitable"
    POSSIBLE = "possible"
    SOME_CONSIDERATIONS = "some_considerations"
    NO_FREE_SEASON = "no_free_season"


class Reason(StrEnum):
    GOOD_ROTATION_INTERVAL = "good_rotation_interval"
    SAME_CROP_RECENT = "same_crop_recent"
    SAME_FAMILY_RECENT = "same_family_recent"
    NO_HISTORY = "no_history"
    COMPATIBLE_NEIGHBOR = "compatible_neighbor"
    LESS_COMPATIBLE_NEIGHBOR = "less_compatible_neighbor"
    FITS_SEASON = "fits_season"
    LIMITED_SEASON = "limited_season"
    TIMING_CONFLICT = "timing_conflict"


@dataclass(frozen=True)
class Assessment:
    score: int  # 0–100
    band: Band
    reasons: tuple[Reason, ...]


@dataclass(frozen=True)
class Suggestion:
    bed_id: int
    crop_id: int
    window: Window


@dataclass(frozen=True)
class Unplaced:
    crop_id: int
    count: int


@dataclass
class LayoutResult:
    suggestions: list[Suggestion]
    unplaced: list[Unplaced]
