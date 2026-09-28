import pytest
from fastapi.testclient import TestClient

from tests.test_gardens import make_bed, make_garden


@pytest.fixture
def bed(client: TestClient, auth_headers: dict[str, str], catalog: dict[str, int]) -> dict:
    return make_bed(client, auth_headers, make_garden(client, auth_headers)["id"])


def add(client: TestClient, headers: dict[str, str], bed_id: int, **body):
    return client.post(f"/beds/{bed_id}/plantings", headers=headers, json=body)


def test_sequential_and_default_plantings(
    client: TestClient, auth_headers: dict[str, str], bed: dict, catalog: dict[str, int]
) -> None:
    lettuce = add(
        client,
        auth_headers,
        bed["id"],
        crop_id=catalog["lettuce"],
        year=2025,
        start_month="2025-04",
        end_month="2025-06",
    )
    assert lettuce.status_code == 201
    beans = add(
        client,
        auth_headers,
        bed["id"],
        crop_id=catalog["bush-bean"],
        year=2025,
        start_month="2025-06",
        end_month="2025-09",
    ).json()
    assert beans["coverage"] == 1.0
    garlic = add(client, auth_headers, bed["id"], crop_id=catalog["garlic"], year=2026).json()
    assert (garlic["start_month"], garlic["end_month"]) == ("2025-10", "2026-07")
    history = client.get(f"/beds/{bed['id']}/plantings", headers=auth_headers).json()
    assert [p["id"] for p in history] == [garlic["id"], beans["id"], lettuce.json()["id"]]

    garden_history = client.get(
        f"/gardens/{bed['garden_id']}/plantings?year_from=2026", headers=auth_headers
    ).json()
    assert [p["id"] for p in garden_history] == [garlic["id"]]

    updated = client.put(
        f"/plantings/{beans['id']}",
        headers=auth_headers,
        json={"crop_id": catalog["pea"], "year": 2025},
    ).json()
    assert (updated["crop_id"], updated["start_month"], updated["end_month"]) == (
        catalog["pea"],
        "2025-05",
        "2025-08",
    )
    assert client.delete(f"/plantings/{beans['id']}", headers=auth_headers).status_code == 204
    assert (
        client.put(
            f"/plantings/{beans['id']}", headers=auth_headers, json={"crop_id": 1, "year": 2025}
        ).status_code
        == 404
    )


def test_overlapping_history_is_accepted(
    client: TestClient, auth_headers: dict[str, str], bed: dict, catalog: dict[str, int]
) -> None:
    # History is approximate guidance data (D009); overlaps are not rejected.
    for crop in ("potato", "carrot"):
        assert (
            add(client, auth_headers, bed["id"], crop_id=catalog[crop], year=2024).status_code
            == 201
        )


@pytest.mark.parametrize(
    "body",
    [
        {"year": 2025, "start_month": "2025-06", "end_month": "2025-04"},
        {"year": 2025, "start_month": "2025-06"},
        {"year": 2026, "start_month": "2025-04", "end_month": "2025-06"},
        {"year": 2025, "start_month": "2025-13", "end_month": "2025-12"},
        {"year": 2025, "start_month": "2025-4", "end_month": "2025-06"},
        {"year": 2025, "start_month": "2025-04-01", "end_month": "2025-06"},
        {"year": 2025, "start_month": "2023-01", "end_month": "2025-06"},
        {"year": 1800},
        {"year": 2025, "coverage": 0.5},
    ],
)
def test_planting_validation(
    client: TestClient, auth_headers: dict[str, str], bed: dict, catalog: dict[str, int], body: dict
) -> None:
    response = add(client, auth_headers, bed["id"], crop_id=catalog["potato"], **body)
    assert response.status_code == 422


def test_unknown_crop(client: TestClient, auth_headers: dict[str, str], bed: dict) -> None:
    response = add(client, auth_headers, bed["id"], crop_id=9999, year=2025)
    assert response.status_code == 422
    assert response.json() == {"detail": "Unknown crop"}


def test_planting_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    bed: dict,
    catalog: dict[str, int],
) -> None:
    planting = add(client, auth_headers, bed["id"], crop_id=catalog["potato"], year=2025).json()
    body = {"crop_id": catalog["potato"], "year": 2025}
    assert add(client, other_headers, bed["id"], **body).status_code == 404
    path = f"/plantings/{planting['id']}"
    assert client.put(path, headers=other_headers, json=body).status_code == 404
    assert client.delete(path, headers=other_headers).status_code == 404
    assert len(client.get(f"/beds/{bed['id']}/plantings", headers=auth_headers).json()) == 1
