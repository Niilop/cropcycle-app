from pathlib import Path

from scripts.export_openapi import openapi_json

SNAPSHOT = Path(__file__).resolve().parents[1] / "mobile" / "src" / "api" / "openapi.json"


def test_mobile_api_snapshot_is_current() -> None:
    # The mobile app's types are generated from this file (D010).
    assert SNAPSHOT.read_text(encoding="utf-8") == openapi_json(), (
        "The API changed: run `npm --prefix mobile run api:types` and commit the result."
    )
