import pytest
from fastapi.testclient import TestClient

from tests.test_gardens import make_bed, make_garden


@pytest.fixture
def garden(client: TestClient, auth_headers: dict[str, str], catalog: dict[str, int]) -> dict:
    garden = make_garden(client, auth_headers)
    # Beds 3 m apart: no neighbour effects unless a test adds them.
    garden["beds"] = [
        make_bed(client, auth_headers, garden["id"], name=f"Bed {i}", x=i * 3.0) for i in range(4)
    ]
    return garden


def create_plan(client: TestClient, headers: dict[str, str], garden: dict, year: int = 2027):
    response = client.post(
        "/plans", headers=headers, json={"garden_id": garden["id"], "year": year}
    )
    assert response.status_code == 201
    return response.json()


def request_crop(client: TestClient, headers: dict[str, str], plan_id: int, crop: int, n: int):
    response = client.post(
        f"/plans/{plan_id}/crops", headers=headers, json={"crop_id": crop, "quantity": n}
    )
    assert response.status_code in (200, 201)


def fill(client: TestClient, headers: dict[str, str], plan_id: int) -> dict:
    response = client.post(f"/plans/{plan_id}/generate-layout", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_fill_remaining_respects_manual_choices(
    client: TestClient, auth_headers: dict[str, str], garden: dict, catalog: dict[str, int]
) -> None:
    plan = create_plan(client, auth_headers, garden)
    beds = [bed["id"] for bed in garden["beds"]]
    for crop, count in (("carrot", 2), ("potato", 1), ("onion", 1)):
        request_crop(client, auth_headers, plan["id"], catalog[crop], count)
    manual = client.post(
        f"/plans/{plan['id']}/placements",
        headers=auth_headers,
        json={"bed_id": beds[0], "crop_id": catalog["carrot"]},
    ).json()

    result = fill(client, auth_headers, plan["id"])
    placements = result["plan"]["placements"]
    assert result["unplaced"] == []
    assert [p for p in placements if p["id"] == manual["id"]][0]["bed_id"] == beds[0]
    suggested = [p for p in placements if p["source"] == "suggested"]
    assert sorted(p["crop_id"] for p in suggested) == sorted(
        [catalog["carrot"], catalog["potato"], catalog["onion"]]
    )
    assert all(not p["locked"] and p["assessment"]["band"] for p in suggested)
    assert beds[0] not in {p["bed_id"] for p in suggested}
    counts = {c["crop_id"]: (c["placed"], c["quantity"]) for c in result["plan"]["crops"]}
    assert counts[catalog["carrot"]] == (2, 2)

    # Accepting a suggestion (locking it) makes it the user's; regenerating keeps it.
    kept = suggested[0]
    client.put(
        f"/plan-placements/{kept['id']}",
        headers=auth_headers,
        json={"bed_id": kept["bed_id"], "crop_id": kept["crop_id"], "locked": True},
    )
    again = fill(client, auth_headers, plan["id"])["plan"]["placements"]
    ids = {p["id"] for p in again}
    assert {manual["id"], kept["id"]} <= ids
    assert len(again) == 4
    by_id = {p["id"]: p for p in again}
    assert (by_id[kept["id"]]["source"], by_id[kept["id"]]["locked"]) == ("manual", True)
    assert sorted(p["source"] for p in again) == ["manual", "manual", "suggested", "suggested"]
    assert fill(client, auth_headers, plan["id"])["plan"]["placements"] == again


def test_fill_remaining_follows_rotation_and_reports_unplaced(
    client: TestClient, auth_headers: dict[str, str], garden: dict, catalog: dict[str, int]
) -> None:
    beds = [bed["id"] for bed in garden["beds"]]
    for bed in beds[:3]:
        response = client.post(
            f"/beds/{bed}/plantings",
            headers=auth_headers,
            json={"crop_id": catalog["potato"], "year": 2026},
        )
        assert response.status_code == 201
    plan = create_plan(client, auth_headers, garden)
    request_crop(client, auth_headers, plan["id"], catalog["tomato"], 1)
    result = fill(client, auth_headers, plan["id"])
    # Tomato shares the potato family; the only bed without it last year is chosen.
    [placement] = result["plan"]["placements"]
    assert placement["bed_id"] == beds[3]
    assert placement["assessment"]["reasons"][0] == "no_history"

    request_crop(client, auth_headers, plan["id"], catalog["tomato"], 6)
    result = fill(client, auth_headers, plan["id"])
    assert len(result["plan"]["placements"]) == 4
    assert result["unplaced"] == [
        {"crop_id": catalog["tomato"], "count": 2, "reason": "no_free_season"}
    ]
    families = {
        p["assessment"]["reasons"][0]
        for p in result["plan"]["placements"]
        if p["bed_id"] != beds[3]
    }
    assert families == {"same_family_recent"}


def test_next_years_plan_reserves_the_autumn(
    client: TestClient, auth_headers: dict[str, str], garden: dict, catalog: dict[str, int]
) -> None:
    beds = [bed["id"] for bed in garden["beds"]]
    for bed in beds[1:]:
        client.delete(f"/beds/{bed}", headers=auth_headers)
    next_year = create_plan(client, auth_headers, garden, 2028)
    response = client.post(
        f"/plans/{next_year['id']}/placements",
        headers=auth_headers,
        json={
            "bed_id": beds[0],
            "crop_id": catalog["garlic"],
            "start_month": "2027-09",
            "end_month": "2028-07",
        },
    )
    assert response.status_code == 201
    plan = create_plan(client, auth_headers, garden)
    request_crop(client, auth_headers, plan["id"], catalog["white-cabbage"], 1)
    request_crop(client, auth_headers, plan["id"], catalog["early-potato"], 1)
    result = fill(client, auth_headers, plan["id"])
    # Cabbage (May–Oct) would clash with the garlic; the early potato (May–Jul) fits.
    assert [p["crop_id"] for p in result["plan"]["placements"]] == [catalog["early-potato"]]
    assert result["unplaced"][0]["crop_id"] == catalog["white-cabbage"]

    suitability = client.get(
        f"/plans/{plan['id']}/suitability?crop_id={catalog['white-cabbage']}",
        headers=auth_headers,
    ).json()
    assert suitability == [
        {
            "bed_id": beds[0],
            "start_month": "2027-05",
            "end_month": "2027-10",
            "assessment": {
                "score": suitability[0]["assessment"]["score"],
                "band": "no_free_season",
                "reasons": ["good_rotation_interval", "timing_conflict"],
            },
        }
    ]


def test_suitability_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    garden: dict,
    catalog: dict[str, int],
) -> None:
    beds = [bed["id"] for bed in garden["beds"]]
    client.post(
        f"/beds/{beds[0]}/plantings",
        headers=auth_headers,
        json={"crop_id": catalog["carrot"], "year": 2026},
    )
    client.delete(f"/beds/{beds[3]}", headers=auth_headers)
    plan = create_plan(client, auth_headers, garden)
    path = f"/plans/{plan['id']}/suitability?crop_id={catalog['carrot']}"
    result = {item["bed_id"]: item for item in client.get(path, headers=auth_headers).json()}
    assert set(result) == set(beds[:3])
    assert result[beds[0]]["assessment"]["reasons"][0] == "same_crop_recent"
    assert result[beds[0]]["assessment"]["band"] == "some_considerations"
    assert result[beds[1]]["assessment"] == {
        "score": 100,
        "band": "very_suitable",
        "reasons": ["no_history", "fits_season"],
    }
    assert client.get(path, headers=other_headers).status_code == 404
    assert client.get(path).status_code == 401
    unknown = client.get(f"/plans/{plan['id']}/suitability?crop_id=9999", headers=auth_headers)
    assert unknown.status_code == 422


def test_generate_requires_draft_and_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    garden: dict,
    catalog: dict[str, int],
) -> None:
    plan = create_plan(client, auth_headers, garden)
    path = f"/plans/{plan['id']}/generate-layout"
    assert client.post(path, headers=other_headers).status_code == 404
    assert client.post(path).status_code == 401
    client.post(f"/plans/{plan['id']}/complete", headers=auth_headers)
    assert client.post(path, headers=auth_headers).status_code == 409
