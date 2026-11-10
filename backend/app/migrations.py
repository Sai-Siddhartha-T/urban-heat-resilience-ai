"""Small, versioned, non-destructive schema migration runner.

The project previously called ``metadata.create_all`` at every startup, which
cannot record schema history or safely evolve a deployed database.  Migrations
below are append-only; each revision is recorded after it succeeds.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.db import Base, DataAsset, Record, SchemaMigration, Zone, engine


MIGRATIONS = (
    ("0001_initial_records_and_zones", (Record.__table__, Zone.__table__)),
    ("0002_provenance_assets", (DataAsset.__table__, SchemaMigration.__table__)),
)


def run_migrations() -> None:
    """Apply outstanding revisions without dropping or rewriting existing data."""
    with engine.begin() as connection:
        SchemaMigration.__table__.create(connection, checkfirst=True)
        applied = {
            row[0]
            for row in connection.execute(text("SELECT revision FROM schema_migrations"))
        }
        for revision, tables in MIGRATIONS:
            if revision in applied:
                continue
            for table in tables:
                table.create(connection, checkfirst=True)
            connection.execute(
                SchemaMigration.__table__.insert().values(
                    revision=revision,
                    applied_at=datetime.now(timezone.utc),
                )
            )


def current_revision() -> str | None:
    """Return the last applied revision for diagnostics and health reporting."""
    if "schema_migrations" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT revision FROM schema_migrations ORDER BY applied_at DESC LIMIT 1")
        ).scalar_one_or_none()
