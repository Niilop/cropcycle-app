import pytest
from fastapi.testclient import TestClient

BED = {"name": "North bed", "x": 0, "y": 0, "width": 1.2, "height": 4}


def make_garden(client: TestClient, headers: dict[str, str], name: str = "Allotment") -> dict:
    response = client.post("/gardens", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()


def make_bed(client: TestClient, headers: dict[str, str], garden_id: int, **changes) -> dict:
    response = client.post(f"/gardens/{garden_id}/beds", headers=headers, json=BED | changes)
    assert response.status_code == 201
    return response.json()


def test_garden_and_bed_lifecycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    garden = make_garden(client, auth_headers, "  Home  ")
    assert garden["name"] == "Home"
    assert client.get("/gardens", headers=auth_headers).json() == [garden]
    bed = make_bed(client, auth_headers, garden["id"])
    other = make_bed(client, auth_headers, garden["id"], name="South bed", x=2)
    moved = client.put(
        f"/beds/{bed['id']}", headers=auth_headers, json=BED | {"x": 1.5, "name": "Renamed"}
    )
    assert moved.status_code == 200
    assert (moved.json()["x"], moved.json()["name"]) == (1.5, "Renamed")

    assert client.delete(f"/beds/{other['id']}", headers=auth_headers).status_code == 204
    detail = client.get(f"/gardens/{garden['id']}", headers=auth_headers).json()
    assert [b["id"] for b in detail["beds"]] == [bed["id"]]
    archived = client.get(
        f"/gardens/{garden['id']}?include_archived=true", headers=auth_headers
    ).json()["beds"]
    assert archived[1]["archived_at"] is not None
    restored = client.post(f"/beds/{other['id']}/restore", headers=auth_headers).json()
    assert restored["archived_at"] is None

    renamed = client.put(f"/gardens/{garden['id']}", headers=auth_headers, json={"name": "Plot"})
    assert renamed.json()["name"] == "Plot"
    assert client.delete(f"/gardens/{garden['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/gardens/{garden['id']}", headers=auth_headers).status_code == 404
    assert client.put(f"/beds/{bed['id']}", headers=auth_headers, json=BED).status_code == 404


def test_garden_ownership(
    client: TestClient, auth_headers: dict[str, str], other_headers: dict[str, str]
) -> None:
    garden = make_garden(client, auth_headers)
    bed = make_bed(client, auth_headers, garden["id"])
    assert client.get("/gardens", headers=other_headers).json() == []
    for method, path, body in [
        ("GET", f"/gardens/{garden['id']}", None),
        ("PUT", f"/gardens/{garden['id']}", {"name": "Mine"}),
        ("DELETE", f"/gardens/{garden['id']}", None),
        ("POST", f"/gardens/{garden['id']}/beds", BED),
        ("PUT", f"/beds/{bed['id']}", BED),
        ("DELETE", f"/beds/{bed['id']}", None),
        ("POST", f"/beds/{bed['id']}/restore", None),
        ("GET", f"/beds/{bed['id']}/plantings", None),
        ("GET", f"/gardens/{garden['id']}/plantings", None),
    ]:
        assert client.request(method, path, headers=other_headers, json=body).status_code == 404
        assert client.request(method, path, json=body).status_code == 401
    assert client.get(f"/gardens/{garden['id']}", headers=auth_headers).json()["beds"][0] == bed


@pytest.mark.parametrize(
    "changes",
    [
        {"width": 0},
        {"height": -1},
        {"name": " "},
        {"x": None},
        {"x": 5000},
        {"garden_id": 2},
    ],
)
def test_bed_validation(client: TestClient, auth_headers: dict[str, str], changes: dict) -> None:
    garden = make_garden(client, auth_headers)
    response = client.post(
        f"/gardens/{garden['id']}/beds", headers=auth_headers, json=BED | changes
    )
    assert response.status_code == 422
