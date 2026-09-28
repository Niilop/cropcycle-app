from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.database import Bed, Garden, Planting
from backend.seed import load_catalog, read_catalog

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    settings = get_settings().model_copy(update={"database_url": url})
    monkeypatch.setattr("backend.core.config.get_settings", lambda: settings)
    return url


@pytest.fixture
def migration_config(database_url: str) -> Config:
    return Config("backend/alembic.ini")


def test_catalog_migration_preserves_items(migration_config: Config, database_url: str) -> None:
    command.upgrade(migration_config, "0001_core")
    engine = create_engine(database_url)
    metadata = MetaData()
    users = Table("users", metadata, autoload_with=engine)
    catalogs = Table("data_catalogs", metadata, autoload_with=engine)
    with engine.begin() as connection:
        connection.execute(users.insert().values(user_row()))
        connection.execute(
            catalogs.insert().values(
                id=1,
                user_id=1,
                name="Keep this",
                description="Keep these details",
                file_path="/old/file.csv",
                data_metadata={"num_rows": 10},
                created_at=CREATED,
                updated_at=CREATED,
            )
        )
    command.upgrade(migration_config, "0002_items")
    items = Table("items", MetaData(), autoload_with=engine)
    with engine.connect() as connection:
        item = connection.execute(select(items)).mappings().one()
    assert (item["owner_id"], item["title"], item["description"]) == (
        1,
        "Keep this",
        "Keep these details",
    )
    command.downgrade(migration_config, "0001_core")
    with engine.connect() as connection:
        restored = connection.execute(select(catalogs)).mappings().one()
    assert restored["name"] == "Keep this"
    assert restored["file_path"] == ""
    engine.dispose()


def test_crop_domain_migration(migration_config: Config, database_url: str) -> None:
    command.upgrade(migration_config, "0002_items")
    engine = create_engine(database_url)
    users = Table("users", MetaData(), autoload_with=engine)
    with engine.begin() as connection:
        connection.execute(users.insert().values(user_row()))
    command.upgrade(migration_config, "head")
    command.check(migration_config)
    tables = set(inspect(engine).get_table_names())
    assert {"items", "background_jobs"}.isdisjoint(tables)
    assert {"gardens", "beds", "plantings", "plans", "plan_placements", "crops"} <= tables
    with Session(engine) as session:
        load_catalog(session, read_catalog())
        garden = Garden(user_id=1, name="Allotment")
        garden.beds.append(Bed(name="A", x=0, y=0, width=1.2, height=3))
        session.add(garden)
        session.flush()
        session.add(
            Planting(
                bed_id=garden.beds[0].id,
                crop_id=1,
                year=2026,
                start_month=date(2026, 5, 1),
                end_month=date(2026, 9, 1),
            )
        )
        session.commit()
    command.downgrade(migration_config, "0002_items")
    tables = set(inspect(engine).get_table_names())
    assert {"items", "background_jobs", "users"} <= tables
    assert "gardens" not in tables
    command.upgrade(migration_config, "head")
    command.downgrade(migration_config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def user_row() -> dict:
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "tester",
        "password_hash": "unused",
        "settings": {},
        "created_at": CREATED,
        "updated_at": CREATED,
    }
