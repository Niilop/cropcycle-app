"""Idempotent loader for the shared crop catalogue (D007)."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import (
    CompanionRule,
    Compatibility,
    Crop,
    CropFamily,
    RotationRule,
)

CATALOG_PATH = Path(__file__).with_name("catalog.json")
REQUIRED_LOCALES = ("en", "fi")


class CatalogError(ValueError):
    pass


@dataclass
class SeedReport:
    families_added: int = 0
    crops_added: int = 0
    rows_updated: int = 0
    rules_removed: int = 0


def read_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_catalog(data)
    return data


def _check_names(slug: str, names: object) -> None:
    if not isinstance(names, dict) or any(
        not isinstance(names.get(locale), str) or not names[locale].strip()
        for locale in REQUIRED_LOCALES
    ):
        raise CatalogError(f"{slug}: names need non-empty {', '.join(REQUIRED_LOCALES)}")


def _check_unique(kind: str, keys: list[Any]) -> None:
    if len(keys) != len(set(keys)):
        raise CatalogError(f"Duplicate {kind} entries")


def validate_catalog(data: dict[str, Any]) -> None:
    families = {family["slug"] for family in data["families"]}
    _check_unique("family", [family["slug"] for family in data["families"]])
    _check_unique("crop", [crop["slug"] for crop in data["crops"]])
    for family in data["families"]:
        _check_names(family["slug"], family["names"])
    for crop in data["crops"]:
        slug = crop["slug"]
        _check_names(slug, crop["names"])
        if crop["family"] not in families:
            raise CatalogError(f"{slug}: unknown family {crop['family']}")
        start, end = crop["default_start_month"], crop["default_end_month"]
        offset = crop.get("default_start_year_offset", 0)
        if not (1 <= start <= 12 and 1 <= end <= 12) or offset not in (-1, 0):
            raise CatalogError(f"{slug}: invalid default window")
        if offset == -1 and end >= start:
            raise CatalogError(f"{slug}: a window starting the previous year must cross new year")
    crops = {crop["slug"] for crop in data["crops"]}
    targets = []
    for rule in data["rotation_rules"]:
        if ("crop" in rule) == ("family" in rule):
            raise CatalogError("Rotation rules need exactly one of crop or family")
        if rule.get("crop", rule.get("family")) not in (crops if "crop" in rule else families):
            raise CatalogError(f"Rotation rule for unknown target {rule}")
        if rule["preferred_gap_years"] < 0 or rule["weight"] <= 0:
            raise CatalogError(f"Invalid rotation rule {rule}")
        targets.append(("crop", rule["crop"]) if "crop" in rule else ("family", rule["family"]))
    _check_unique("rotation rule", targets)
    pairs = []
    for rule in data["companion_rules"]:
        a, b = rule["crops"]
        if a == b or a not in crops or b not in crops:
            raise CatalogError(f"Invalid companion pair {a}, {b}")
        Compatibility(rule["compatibility"])
        if rule["weight"] <= 0:
            raise CatalogError(f"Invalid companion weight for {a}, {b}")
        pairs.append(frozenset((a, b)))
    _check_unique("companion rule", pairs)


def _upsert(db: Session, model: type, slug: str, values: dict[str, Any], report: SeedReport):
    row = db.scalar(select(model).where(model.slug == slug))
    if row is None:
        row = model(slug=slug, **values)
        db.add(row)
        if model is CropFamily:
            report.families_added += 1
        else:
            report.crops_added += 1
    elif any(getattr(row, key) != value for key, value in values.items()):
        for key, value in values.items():
            setattr(row, key, value)
        report.rows_updated += 1
    return row


def load_catalog(db: Session, data: dict[str, Any]) -> SeedReport:
    """Upsert families and crops by slug and sync rules to the file, in one transaction.

    Families and crops missing from the file are kept because user history may reference them.
    """
    validate_catalog(data)
    report = SeedReport()
    families = {
        family["slug"]: _upsert(db, CropFamily, family["slug"], {"names": family["names"]}, report)
        for family in data["families"]
    }
    db.flush()
    crops = {}
    for crop in data["crops"]:
        values = {
            "names": crop["names"],
            "family_id": families[crop["family"]].id,
            "default_start_month": crop["default_start_month"],
            "default_end_month": crop["default_end_month"],
            "default_start_year_offset": crop.get("default_start_year_offset", 0),
        }
        crops[crop["slug"]] = _upsert(db, Crop, crop["slug"], values, report)
    db.flush()

    wanted_rotation = {
        (
            crops[rule["crop"]].id if "crop" in rule else None,
            families[rule["family"]].id if "family" in rule else None,
        ): rule
        for rule in data["rotation_rules"]
    }
    for row in db.scalars(select(RotationRule)):
        rule = wanted_rotation.pop((row.crop_id, row.family_id), None)
        if rule is None:
            db.delete(row)
            report.rules_removed += 1
        elif (row.preferred_gap_years, row.weight) != (rule["preferred_gap_years"], rule["weight"]):
            row.preferred_gap_years, row.weight = rule["preferred_gap_years"], rule["weight"]
            report.rows_updated += 1
    for (crop_id, family_id), rule in wanted_rotation.items():
        db.add(
            RotationRule(
                crop_id=crop_id,
                family_id=family_id,
                preferred_gap_years=rule["preferred_gap_years"],
                weight=rule["weight"],
            )
        )

    wanted_companion = {}
    for rule in data["companion_rules"]:
        a, b = sorted(crops[slug].id for slug in rule["crops"])
        wanted_companion[(a, b)] = rule
    for row in db.scalars(select(CompanionRule)):
        rule = wanted_companion.pop((row.crop_a_id, row.crop_b_id), None)
        if rule is None:
            db.delete(row)
            report.rules_removed += 1
        elif (row.compatibility, row.weight) != (rule["compatibility"], rule["weight"]):
            row.compatibility, row.weight = Compatibility(rule["compatibility"]), rule["weight"]
            report.rows_updated += 1
    for (a, b), rule in wanted_companion.items():
        db.add(
            CompanionRule(
                crop_a_id=a,
                crop_b_id=b,
                compatibility=Compatibility(rule["compatibility"]),
                weight=rule["weight"],
            )
        )
    db.commit()
    return report
