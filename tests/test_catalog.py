import copy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.database import CompanionRule, Crop, CropFamily, RotationRule
from backend.seed import CatalogError, load_catalog, read_catalog, validate_catalog
from backend.services.windows import default_window


def counts(db: Session) -> tuple[int, ...]:
    return tuple(
        db.scalar(select(func.count()).select_from(model))
        for model in (CropFamily, Crop, RotationRule, CompanionRule)
    )


def test_seed_catalog_is_valid_and_idempotent(db: Session) -> None:
    data = read_catalog()
    assert 30 <= len(data["crops"]) <= 50
    report = load_catalog(db, data)
    assert report.crops_added == len(data["crops"])
    first = counts(db)
    again = load_catalog(db, data)
    assert (again.families_added, again.crops_added, again.rows_updated, again.rules_removed) == (
        0,
        0,
        0,
        0,
    )
    assert counts(db) == first
    for crop in db.scalars(select(Crop)):
        assert crop.names["en"] and crop.names["fi"]
        start, end = default_window(crop, 2027)
        assert start.year <= 2027 <= end.year


def test_seed_updates_and_syncs_rules(db: Session) -> None:
    data = read_catalog()
    load_catalog(db, data)
    changed = copy.deepcopy(data)
    changed["crops"][0]["names"]["fi"] = "Muutettu"
    removed = changed["companion_rules"].pop()
    changed["crops"].pop()  # Crops missing from the file are kept for history.
    changed["companion_rules"] = [
        rule
        for rule in changed["companion_rules"]
        if data["crops"][-1]["slug"] not in rule["crops"]
    ]
    report = load_catalog(db, changed)
    assert report.rows_updated == 1
    assert report.rules_removed >= 1
    assert db.scalar(select(Crop).where(Crop.slug == data["crops"][-1]["slug"])) is not None
    assert db.scalar(select(Crop).where(Crop.slug == data["crops"][0]["slug"])).names["fi"] == (
        "Muutettu"
    )
    load_catalog(db, data)
    a, b = (db.scalar(select(Crop.id).where(Crop.slug == slug)) for slug in removed["crops"])
    assert db.scalar(
        select(CompanionRule).where(
            CompanionRule.crop_a_id == min(a, b), CompanionRule.crop_b_id == max(a, b)
        )
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["crops"][0]["names"].pop("fi"),
        lambda d: d["crops"][0].update(family="unknown"),
        lambda d: d["crops"][0].update(default_start_month=13),
        lambda d: d["crops"][0].update(default_start_year_offset=-1),
        lambda d: d["crops"].append(copy.deepcopy(d["crops"][0])),
        lambda d: d["companion_rules"].append(
            {"crops": ["carrot", "carrot"], "compatibility": "positive", "weight": 1}
        ),
        lambda d: d["companion_rules"].append(
            {"crops": ["onion", "carrot"], "compatibility": "positive", "weight": 1}
        ),
        lambda d: d["rotation_rules"].append({"preferred_gap_years": 2, "weight": 1}),
    ],
)
def test_invalid_catalog_rejected(mutate) -> None:
    data = read_catalog()
    mutate(data)
    with pytest.raises(CatalogError):
        validate_catalog(data)


def test_catalog_endpoints(
    client: TestClient, auth_headers: dict[str, str], catalog: dict[str, int]
) -> None:
    for path in ("/crops", "/crop-families", "/rotation-rules", "/companion-rules"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth_headers).status_code == 200
    crops = {crop["slug"]: crop for crop in client.get("/crops", headers=auth_headers).json()}
    assert crops["garlic"]["names"]["fi"].startswith("Valkosipuli")
    assert (crops["garlic"]["default_start_month"], crops["garlic"]["default_end_month"]) == (10, 7)
    assert crops["garlic"]["default_start_year_offset"] == -1
