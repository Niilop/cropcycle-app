import time

import pytest

from backend.services.layout import (
    Band,
    BedShape,
    Catalog,
    Compat,
    CropInfo,
    Garden,
    Occupant,
    Reason,
    Rule,
    Scorer,
    Window,
    generate_layout,
    month_index,
)
from backend.services.layout.scoring import gap_score

YEAR = 2027


def season(start: int, end: int, year: int = YEAR) -> Window:
    return Window(month_index(year, start), month_index(year, end))


def far_beds(count: int) -> list[BedShape]:
    """Beds 3 m apart, so none are neighbours."""
    return [BedShape(i + 1, i * 3.0, 0, 1, 1) for i in range(count)]


def history(key: str, bed: int, crop: int, year: int) -> Occupant:
    return Occupant(key, bed, crop, season(5, 9, year), year)


def catalog(**extra) -> Catalog:
    crops = {
        1: CropInfo(1, 10, season(5, 9)),  # e.g. potato
        2: CropInfo(2, 10, season(6, 9)),  # same family as 1
        3: CropInfo(3, 20, season(5, 9)),  # e.g. carrot
        4: CropInfo(4, 30, season(5, 7)),  # early crop
        5: CropInfo(5, 40, season(7, 9)),  # late crop
    }
    return Catalog(
        crops=crops,
        crop_rules={1: Rule(4, 1.0)},
        family_rules={10: Rule(4, 1.0), 20: Rule(3, 1.0)},
        **extra,
    )


def assess(cat: Catalog, garden: Garden, crop: int, bed: int, plan: list[Occupant] = ()):
    scorer = Scorer(cat, garden)
    return scorer.assess(crop, bed, cat.crops[crop].default_window, scorer.index(plan))


@pytest.mark.parametrize(
    "gap,rule,expected",
    [
        (None, Rule(4, 1), 1.0),
        (4, Rule(4, 1), 1.0),
        (1, Rule(4, 1), 0.0),
        (3, Rule(4, 1), 2 / 3),
        (0, Rule(0, 1), 1.0),
        (0, Rule(1, 1), 0.0),
        (3, Rule(4, 1.5), 0.5),
    ],
)
def test_gap_score(gap: int | None, rule: Rule, expected: float) -> None:
    assert gap_score(gap, rule) == pytest.approx(expected)


def test_windows_allow_one_month_handover() -> None:
    lettuce, beans = season(4, 6), season(6, 9)
    assert lettuce.extra_overlap(beans) == 0
    assert season(5, 7).extra_overlap(beans) == 1
    assert season(5, 9).extra_overlap(beans) == 3
    garlic = Window(month_index(YEAR - 1, 10), month_index(YEAR, 7))
    assert garlic.extra_overlap(season(8, 9)) == 0
    assert garlic.extra_overlap(season(5, 9)) == 2


def test_neighbours_by_edge_distance() -> None:
    beds = [BedShape(1, 0, 0, 1, 2), BedShape(2, 2, 0, 1, 2), BedShape(3, 3.5, 0, 1, 2)]
    garden = Garden(YEAR, beds, [])
    assert garden.neighbors == {1: {2}, 2: {1, 3}, 3: {2}}


def test_rotation_bands_and_reasons() -> None:
    cat = catalog()
    garden = Garden(
        YEAR,
        far_beds(4),
        [
            history("h1", 1, 1, YEAR - 1),  # same crop last year
            history("h2", 2, 2, YEAR - 1),  # same family last year
            history("h3", 3, 3, YEAR - 5),  # unrelated, long ago
        ],
    )
    same_crop = assess(cat, garden, 1, 1)
    assert same_crop.band == Band.SOME_CONSIDERATIONS
    assert same_crop.reasons[0] == Reason.SAME_CROP_RECENT
    same_family = assess(cat, garden, 1, 2)
    assert same_family.band == Band.POSSIBLE
    assert same_family.reasons[0] == Reason.SAME_FAMILY_RECENT
    good = assess(cat, garden, 1, 3)
    assert (good.score, good.band) == (100, Band.VERY_SUITABLE)
    assert good.reasons == (Reason.GOOD_ROTATION_INTERVAL, Reason.FITS_SEASON)
    unknown = assess(cat, garden, 1, 4)
    assert unknown.reasons == (Reason.NO_HISTORY, Reason.FITS_SEASON)


def test_neighbours_and_timing() -> None:
    cat = catalog(companions={(1, 3): (Compat.NEGATIVE, 1.0), (3, 4): (Compat.POSITIVE, 1.0)})
    beds = [BedShape(1, 0, 0, 1, 1), BedShape(2, 1.5, 0, 1, 1)]
    garden = Garden(YEAR, beds, [])
    plan = [Occupant("p1", 2, 1, season(5, 9), YEAR)]
    carrot = assess(cat, garden, 3, 1, plan)
    assert (carrot.score, carrot.band) == (90, Band.VERY_SUITABLE)
    assert Reason.LESS_COMPATIBLE_NEIGHBOR in carrot.reasons
    friendly = assess(cat, garden, 3, 1, [Occupant("p1", 2, 4, season(5, 7), YEAR)])
    assert friendly.score == 100 and Reason.COMPATIBLE_NEIGHBOR in friendly.reasons

    early = [Occupant("p2", 1, 4, season(5, 7), YEAR)]
    assert assess(cat, garden, 5, 1, early).reasons[-1] == Reason.FITS_SEASON
    limited = assess(cat, garden, 3, 1, [Occupant("p2", 1, 4, season(4, 6), YEAR)])
    assert limited.reasons[-1] == Reason.LIMITED_SEASON
    assert limited.band != Band.NO_FREE_SEASON
    conflict = assess(cat, garden, 3, 1, early)
    assert conflict.reasons[-1] == Reason.TIMING_CONFLICT
    assert conflict.band == Band.NO_FREE_SEASON


def test_fixed_placements_are_kept_and_beds_shared_sequentially() -> None:
    cat = catalog()
    garden = Garden(YEAR, far_beds(2), [])
    fixed = [Occupant("placement:1", 1, 3, season(5, 9), YEAR)]
    result = generate_layout(cat, garden, fixed, {4: 1, 5: 1, 1: 1})
    # Bed 1 is taken all season; the early and late crops share bed 2 via handover.
    placed = {(s.bed_id, s.crop_id) for s in result.suggestions}
    assert placed == {(2, 4), (2, 5)}
    assert [(u.crop_id, u.count) for u in result.unplaced] == [(1, 1)]


def test_avoids_recent_rotation_and_other_years_occupancy() -> None:
    cat = catalog()
    garlic_next_year = Occupant(
        "other-plan:9", 2, 3, Window(month_index(YEAR, 8), month_index(YEAR + 1, 7)), YEAR + 1
    )
    garden = Garden(YEAR, far_beds(3), [history("h1", 1, 1, YEAR - 1), garlic_next_year])
    result = generate_layout(cat, garden, [], {1: 1})
    # Bed 1 grew the crop last year; bed 2 is reserved from August for next year's crop.
    assert [(s.bed_id, s.crop_id) for s in result.suggestions] == [(3, 1)]


def test_optimizes_the_whole_plan() -> None:
    cat = catalog()
    # Crop 1 slightly prefers bed 1; crop 3 strongly needs bed 1 (its family grew in bed 2).
    garden = Garden(
        YEAR, far_beds(2), [history("h1", 2, 2, YEAR - 2), history("h2", 2, 3, YEAR - 1)]
    )
    scorer = Scorer(cat, garden)
    empty = scorer.index([])
    assert (
        scorer.assess(1, 1, season(5, 9), empty).score
        > scorer.assess(1, 2, season(5, 9), empty).score
    )
    result = generate_layout(cat, garden, [], {1: 1, 3: 1})
    assert {(s.bed_id, s.crop_id) for s in result.suggestions} == {(2, 1), (1, 3)}


def test_layout_is_deterministic_and_fast() -> None:
    families = {crop: 10 + crop % 9 for crop in range(1, 31)}
    cat = Catalog(
        crops={
            crop: CropInfo(crop, family, season(4 + crop % 3, 7 + crop % 3))
            for crop, family in families.items()
        },
        family_rules={family: Rule(3, 1.0) for family in set(families.values())},
        companions={
            (a, a + 1): (Compat.NEGATIVE if a % 2 else Compat.POSITIVE, 1.0) for a in range(1, 30)
        },
    )
    beds = [BedShape(i + 1, (i % 10) * 1.5, (i // 10) * 2.5, 1.2, 2) for i in range(50)]
    background = [
        history(f"h{bed}-{year}", bed, 1 + (bed * year) % 30, year)
        for bed in range(1, 51)
        for year in range(YEAR - 4, YEAR)
    ]
    garden = Garden(YEAR, beds, background)
    demand = {crop: 1 + crop % 2 for crop in range(1, 31)}
    started = time.monotonic()
    first = generate_layout(cat, garden, [], demand)
    assert time.monotonic() - started < 2.0
    assert sum(1 for _ in first.suggestions) + sum(u.count for u in first.unplaced) == 45
    assert generate_layout(cat, garden, [], demand) == first
