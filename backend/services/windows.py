"""Month-granularity planting windows (D012)."""

from datetime import date

from backend.models.database import Crop


def default_window(crop: Crop, year: int) -> tuple[date, date]:
    """The crop's default window for the season `year`; it may start or end in another year."""
    start = date(year + crop.default_start_year_offset, crop.default_start_month, 1)
    end_year = start.year + (1 if crop.default_end_month < crop.default_start_month else 0)
    return start, date(end_year, crop.default_end_month, 1)


def touches_year(start: date, end: date, year: int) -> bool:
    return start.year <= year <= end.year
