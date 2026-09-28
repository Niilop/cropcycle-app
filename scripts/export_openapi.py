"""Print the API's OpenAPI schema as JSON; used to generate the mobile app's types (D010)."""

import json
import os


def openapi_json() -> str:
    # The schema does not depend on a real database or secret, but settings require them.
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("SECRET_KEY", "openapi-export-only-secret-with-32-bytes")
    from backend.main import create_app

    schema = create_app().openapi()
    # The title follows APP_NAME, which local settings may change; keep the snapshot stable.
    schema["info"]["title"] = "CropCycle API"
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    print(openapi_json(), end="")
