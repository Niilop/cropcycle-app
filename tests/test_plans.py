import pytest
from fastapi.testclient import TestClient

from tests.test_gardens import make_bed, make_garden


@pytest.fixture
def garden(client: TestClient, auth_headers: dict[str, str], catalog: dict[str, int]) -> dict:
    garden = make_garden(client, auth_headers)
    garden["beds"] = [
        make_bed(client, auth_headers, garden["id"], name=name, x=index * 2)
        for index, name in enumerate("ABC")
    ]
    return garden


@pytest.fixture
def plan(client: TestClient, auth_headers: dict[str, str], garden: dict) -> dict:
    response = client.post(
        "/plans", headers=auth_headers, json={"garden_id": garden["id"], "year": 2027}
    )
    assert response.status_code == 201
    return response.json()


def place(client: TestClient, headers: dict[str, str], plan_id: int, **body):
    return client.post(f"/plans/{plan_id}/placements", headers=headers, json=body)


def test_plan_crops_and_placements(
    client: TestClient,
    auth_headers: dict[str, str],
    garden: dict,
    plan: dict,
    catalog: dict[str, int],
) -> None:
    assert (plan["name"], plan["status"], plan["crops"], plan["placements"]) == (
        "2027",
        "draft",
        [],
        [],
    )
    path = f"/plans/{plan['id']}"
    added = client.post(
        f"{path}/crops", headers=auth_headers, json={"crop_id": catalog["carrot"], "quantity": 1}
    )
    assert added.status_code == 201
    changed = client.post(
        f"{path}/crops", headers=auth_headers, json={"crop_id": catalog["carrot"], "quantity": 2}
    )
    assert changed.status_code == 200
    assert [(c["crop_id"], c["quantity"], c["placed"]) for c in changed.json()["crops"]] == [
        (catalog["carrot"], 2, 0)
    ]

    beds = garden["beds"]
    placement = place(
        client, auth_headers, plan["id"], bed_id=beds[0]["id"], crop_id=catalog["carrot"]
    ).json()
    assert (placement["locked"], placement["source"]) == (True, "manual")
    assert (placement["start_month"], placement["end_month"]) == ("2027-05", "2027-09")
    garlic = place(
        client, auth_headers, plan["id"], bed_id=beds[1]["id"], crop_id=catalog["garlic"]
    ).json()
    assert (garlic["start_month"], garlic["end_month"]) == ("2026-10", "2027-07")
    detail = client.get(path, headers=auth_headers).json()
    assert detail["crops"][0]["placed"] == 1
    assert len(detail["placements"]) == 2

    moved = client.put(
        f"/plan-placements/{placement['id']}",
        headers=auth_headers,
        json={"bed_id": beds[2]["id"], "crop_id": catalog["carrot"], "locked": False},
    ).json()
    assert (moved["bed_id"], moved["locked"], moved["source"]) == (beds[2]["id"], False, "manual")

    assert (
        client.delete(f"{path}/crops/{catalog['carrot']}", headers=auth_headers).status_code == 204
    )
    detail = client.get(path, headers=auth_headers).json()
    assert detail["crops"] == []
    assert [p["crop_id"] for p in detail["placements"]] == [catalog["garlic"]]
    assert (
        client.delete(f"{path}/crops/{catalog['carrot']}", headers=auth_headers).status_code == 404
    )
    assert (
        client.delete(f"/plan-placements/{garlic['id']}", headers=auth_headers).status_code == 204
    )


def test_plan_rules(
    client: TestClient,
    auth_headers: dict[str, str],
    garden: dict,
    plan: dict,
    catalog: dict[str, int],
) -> None:
    duplicate = client.post(
        "/plans", headers=auth_headers, json={"garden_id": garden["id"], "year": 2027}
    )
    assert duplicate.status_code == 409
    listed = client.get(f"/plans?garden_id={garden['id']}", headers=auth_headers).json()
    assert [p["id"] for p in listed] == [plan["id"]]

    bed_id = garden["beds"][0]["id"]
    outside = place(
        client,
        auth_headers,
        plan["id"],
        bed_id=bed_id,
        crop_id=catalog["carrot"],
        start_month="2025-05",
        end_month="2025-09",
    )
    assert outside.status_code == 422
    # Overlapping placements are guidance concerns, not errors (D009).
    for _ in range(2):
        assert (
            place(client, auth_headers, plan["id"], bed_id=bed_id, crop_id=catalog["potato"])
        ).status_code == 201

    client.delete(f"/beds/{bed_id}", headers=auth_headers)
    archived = place(client, auth_headers, plan["id"], bed_id=bed_id, crop_id=catalog["potato"])
    assert archived.status_code == 409

    other_garden = make_garden(client, auth_headers, "Other")
    foreign_bed = make_bed(client, auth_headers, other_garden["id"])
    response = place(
        client, auth_headers, plan["id"], bed_id=foreign_bed["id"], crop_id=catalog["potato"]
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Unknown bed"}
    assert (
        place(client, auth_headers, plan["id"], bed_id=garden["beds"][1]["id"], crop_id=9999)
    ).status_code == 422


def test_complete_plan_writes_history(
    client: TestClient,
    auth_headers: dict[str, str],
    garden: dict,
    plan: dict,
    catalog: dict[str, int],
) -> None:
    path = f"/plans/{plan['id']}"
    beds = garden["beds"]
    placement = place(
        client, auth_headers, plan["id"], bed_id=beds[0]["id"], crop_id=catalog["onion"]
    ).json()
    manual = client.post(
        f"/beds/{beds[0]['id']}/plantings",
        headers=auth_headers,
        json={"crop_id": catalog["lettuce"], "year": 2026},
    ).json()

    completed = client.post(f"{path}/complete", headers=auth_headers).json()
    assert completed["status"] == "completed"
    history = client.get(f"/beds/{beds[0]['id']}/plantings", headers=auth_headers).json()
    from_plan = [p for p in history if p["plan_id"] == plan["id"]]
    assert [(p["crop_id"], p["year"], p["start_month"]) for p in from_plan] == [
        (catalog["onion"], 2027, "2027-05")
    ]

    body = {"bed_id": beds[1]["id"], "crop_id": catalog["onion"]}
    for method, url, json in [
        ("POST", f"{path}/placements", body),
        ("PUT", f"/plan-placements/{placement['id']}", body),
        ("DELETE", f"/plan-placements/{placement['id']}", None),
        ("POST", f"{path}/crops", {"crop_id": catalog["onion"], "quantity": 1}),
    ]:
        assert client.request(method, url, headers=auth_headers, json=json).status_code == 409

    assert client.post(f"{path}/reopen", headers=auth_headers).json()["status"] == "draft"
    client.put(f"/plan-placements/{placement['id']}", headers=auth_headers, json=body)
    client.post(f"{path}/complete", headers=auth_headers)
    history = client.get(f"/gardens/{garden['id']}/plantings", headers=auth_headers).json()
    from_plan = [p for p in history if p["plan_id"] == plan["id"]]
    assert [p["bed_id"] for p in from_plan] == [beds[1]["id"]]
    assert manual["id"] in {p["id"] for p in history}

    assert client.delete(path, headers=auth_headers).status_code == 204
    history = client.get(f"/gardens/{garden['id']}/plantings", headers=auth_headers).json()
    assert len(history) == 2
    assert all(p["plan_id"] is None for p in history)


def test_plan_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    garden: dict,
    plan: dict,
    catalog: dict[str, int],
) -> None:
    placement = place(
        client, auth_headers, plan["id"], bed_id=garden["beds"][0]["id"], crop_id=catalog["pea"]
    ).json()
    other_garden = make_garden(client, other_headers, "Theirs")
    other_bed = make_bed(client, other_headers, other_garden["id"])
    assert (
        client.post(
            "/plans", headers=other_headers, json={"garden_id": garden["id"], "year": 2028}
        ).status_code
        == 422
    )
    assert client.get(f"/plans?garden_id={garden['id']}", headers=other_headers).status_code == 404
    path = f"/plans/{plan['id']}"
    body = {"bed_id": other_bed["id"], "crop_id": catalog["pea"]}
    for method, url, json in [
        ("GET", path, None),
        ("PUT", path, {"name": "Mine"}),
        ("DELETE", path, None),
        ("POST", f"{path}/complete", None),
        ("POST", f"{path}/reopen", None),
        ("POST", f"{path}/crops", {"crop_id": catalog["pea"], "quantity": 1}),
        ("DELETE", f"{path}/crops/{catalog['pea']}", None),
        ("POST", f"{path}/placements", body),
        ("PUT", f"/plan-placements/{placement['id']}", body),
        ("DELETE", f"/plan-placements/{placement['id']}", None),
    ]:
        assert client.request(method, url, headers=other_headers, json=json).status_code == 404
        assert client.request(method, url, json=json).status_code == 401
    stored = client.get(path, headers=auth_headers).json()["placements"][0]
    assert stored["assessment"] is not None
    assert stored | {"assessment": None} == placement
