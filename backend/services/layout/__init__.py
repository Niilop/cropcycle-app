"""Rotation scoring and auto-layout. Pure functions over plain data (D008)."""

from backend.services.layout.model import (
    Assessment,
    Band,
    BedShape,
    Catalog,
    Compat,
    CropInfo,
    Garden,
    LayoutResult,
    Occupant,
    Reason,
    Rule,
    Suggestion,
    Unplaced,
    Window,
    month_index,
)
from backend.services.layout.scoring import Scorer
from backend.services.layout.solver import generate_layout

__all__ = [
    "Assessment",
    "Band",
    "BedShape",
    "Catalog",
    "Compat",
    "CropInfo",
    "Garden",
    "LayoutResult",
    "Occupant",
    "Reason",
    "Rule",
    "Scorer",
    "Suggestion",
    "Unplaced",
    "Window",
    "generate_layout",
    "month_index",
]
