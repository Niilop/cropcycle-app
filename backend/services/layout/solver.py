"""Greedy placement followed by move/swap improvement, optimizing the whole plan (D008).

Replaceable with a constraint solver behind `generate_layout`'s signature.
"""

import time
from collections import Counter

from backend.services.layout.model import (
    Catalog,
    Garden,
    LayoutResult,
    Occupant,
    Suggestion,
    Unplaced,
)
from backend.services.layout.scoring import Scorer

DEFAULT_TIME_BUDGET_S = 1.0
EPSILON = 1e-9


class _State:
    def __init__(self, scorer: Scorer, fixed: list[Occupant]) -> None:
        self.scorer = scorer
        self.year = scorer.garden.year
        self.plan: dict[str, Occupant] = {o.key: o for o in fixed}
        self.suggested: list[str] = []
        self.pending: list[tuple[str, int]] = []
        self.by_bed = scorer.index(fixed)
        self.bed_ids = [bed.id for bed in scorer.garden.beds]

    def feasible(self, crop_id: int, bed_id: int, exclude: str | None = None) -> bool:
        """Free season in the bed, and not the same crop twice in one bed in this year."""
        window = self.scorer.catalog.crops[crop_id].default_window
        for other in self.by_bed.get(bed_id, ()):
            if other.key == exclude:
                continue
            if window.extra_overlap(other.window) > 0:
                return False
            if other.crop_id == crop_id and other.year == self.year:
                return False
        return True

    def affected_beds(self, *beds: int) -> set[int]:
        result = set(beds)
        for bed in beds:
            result |= self.scorer.garden.neighbors.get(bed, set())
        return result

    def objective(self, beds: set[int]) -> float:
        total = 0.0
        for bed in beds:
            for occupant in self.by_bed.get(bed, ()):
                if occupant.key in self.plan:
                    total += self.scorer.evaluate(
                        occupant.crop_id, bed, occupant.window, self.by_bed, occupant.key
                    )[0]
        return total

    def add(self, occupant: Occupant) -> None:
        self.plan[occupant.key] = occupant
        self.by_bed.setdefault(occupant.bed_id, []).append(occupant)

    def remove(self, key: str) -> Occupant:
        occupant = self.plan.pop(key)
        self.by_bed[occupant.bed_id].remove(occupant)
        return occupant

    def moved(self, occupant: Occupant, bed_id: int) -> Occupant:
        return Occupant(occupant.key, bed_id, occupant.crop_id, occupant.window, occupant.year)

    def try_move(self, key: str, bed_id: int) -> bool:
        current = self.plan[key]
        if bed_id == current.bed_id or not self.feasible(current.crop_id, bed_id, key):
            return False
        beds = self.affected_beds(current.bed_id, bed_id)
        before = self.objective(beds)
        self.remove(key)
        self.add(self.moved(current, bed_id))
        if self.objective(beds) > before + EPSILON:
            return True
        self.remove(key)
        self.add(current)
        return False

    def best_bed(self, key: str, crop_id: int) -> int | None:
        """The feasible bed where adding the crop gains the most, or None."""
        window = self.scorer.catalog.crops[crop_id].default_window
        best: tuple[float, int] | None = None
        for bed_id in self.bed_ids:
            if not self.feasible(crop_id, bed_id):
                continue
            beds = self.affected_beds(bed_id)
            before = self.objective(beds)
            self.add(Occupant(key, bed_id, crop_id, window, self.year))
            gain = self.objective(beds) - before
            self.remove(key)
            if best is None or gain > best[0] + EPSILON:
                best = (gain, bed_id)
        return None if best is None else best[1]

    def place(self, key: str, crop_id: int) -> bool:
        bed_id = self.best_bed(key, crop_id)
        if bed_id is None:
            return False
        window = self.scorer.catalog.crops[crop_id].default_window
        self.add(Occupant(key, bed_id, crop_id, window, self.year))
        self.suggested.append(key)
        return True

    def rank(self) -> tuple[int, float]:
        """Placing more requested crops always beats a higher total score."""
        return len(self.suggested), self.objective(set(self.bed_ids))

    def try_insert(self, key: str, crop_id: int) -> bool:
        """Place a pending crop by evicting conflicting suggestions and re-placing them."""
        if key in self.suggested:
            return False
        window = self.scorer.catalog.crops[crop_id].default_window
        before = self.rank()
        for bed_id in self.bed_ids:
            evict = [
                o
                for o in self.by_bed.get(bed_id, ())
                if o.key in self.suggested
                and (
                    window.extra_overlap(o.window) > 0
                    or (o.crop_id == crop_id and o.year == self.year)
                )
            ]
            if not evict:
                continue
            snapshot = (
                dict(self.plan),
                {bed: list(items) for bed, items in self.by_bed.items()},
                list(self.suggested),
            )
            for occupant in evict:
                self.remove(occupant.key)
                self.suggested.remove(occupant.key)
            if self.feasible(crop_id, bed_id):
                self.add(Occupant(key, bed_id, crop_id, window, self.year))
                self.suggested.append(key)
                # Evicted crops and other pending crops may fit elsewhere now.
                waiting = [(o.key, o.crop_id) for o in evict] + [
                    p for p in self.pending if p[0] != key
                ]
                for waiting_key, waiting_crop in waiting:
                    self.place(waiting_key, waiting_crop)
                if self.rank() > (before[0], before[1] + EPSILON):
                    self.pending = [p for p in waiting if p[0] not in self.suggested]
                    return True
            self.plan, self.by_bed, self.suggested = snapshot
        return False

    def try_swap(self, key_a: str, key_b: str) -> bool:
        a, b = self.plan[key_a], self.plan[key_b]
        if a.bed_id == b.bed_id or a.crop_id == b.crop_id:
            return False
        beds = self.affected_beds(a.bed_id, b.bed_id)
        before = self.objective(beds)
        self.remove(key_a)
        self.remove(key_b)
        if self.feasible(a.crop_id, b.bed_id) and self.feasible(b.crop_id, a.bed_id):
            self.add(self.moved(a, b.bed_id))
            self.add(self.moved(b, a.bed_id))
            if self.objective(beds) > before + EPSILON:
                return True
            self.remove(key_a)
            self.remove(key_b)
        self.add(a)
        self.add(b)
        return False


def generate_layout(
    catalog: Catalog,
    garden: Garden,
    fixed: list[Occupant],
    demand: dict[int, int],
    time_budget_s: float = DEFAULT_TIME_BUDGET_S,
) -> LayoutResult:
    """Suggest beds for `demand` (crop id -> count) around `fixed` plan placements.

    Fixed placements never move. Suggestions use each crop's default window and never overlap
    another crop in the same bed beyond a one-month handover.
    """
    deadline = time.monotonic() + time_budget_s
    state = _State(Scorer(catalog, garden), fixed)
    units = [crop for crop in sorted(demand) if crop in catalog.crops for _ in range(demand[crop])]
    # Most constrained first: crops with the fewest free beds.
    options = {crop: sum(state.feasible(crop, bed) for bed in state.bed_ids) for crop in set(units)}
    units.sort(key=lambda crop: (options.get(crop, 0), crop))

    for number, crop_id in enumerate(units):
        key = f"suggested:{number}"
        if not state.place(key, crop_id):
            state.pending.append((key, crop_id))

    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for key, crop_id in list(state.pending):
            if state.try_insert(key, crop_id):
                improved = True
        for key in state.suggested:
            for bed_id in state.bed_ids:
                if state.try_move(key, bed_id):
                    improved = True
            if time.monotonic() >= deadline:
                break
        for i, key_a in enumerate(state.suggested):
            for key_b in state.suggested[i + 1 :]:
                if state.try_swap(key_a, key_b):
                    improved = True
            if time.monotonic() >= deadline:
                break

    suggestions = [
        Suggestion(state.plan[key].bed_id, state.plan[key].crop_id, state.plan[key].window)
        for key in state.suggested
    ]
    suggestions.sort(key=lambda s: (s.bed_id, s.window.start, s.crop_id))
    unplaced = Counter(crop_id for _, crop_id in state.pending)
    return LayoutResult(
        suggestions=suggestions,
        unplaced=[Unplaced(crop, count) for crop, count in sorted(unplaced.items())],
    )
