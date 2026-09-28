"""Load the crop catalogue into the configured database: `make seed`."""

from backend.core.database import SessionLocal
from backend.seed import load_catalog, read_catalog


def main() -> None:
    with SessionLocal() as db:
        report = load_catalog(db, read_catalog())
    print(
        f"Catalogue loaded: {report.families_added} families and {report.crops_added} crops "
        f"added, {report.rows_updated} rows updated, {report.rules_removed} rules removed."
    )


if __name__ == "__main__":
    main()
