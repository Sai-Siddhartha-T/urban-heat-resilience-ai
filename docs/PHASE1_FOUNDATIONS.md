# Phase 1 foundations

## Modes

Normal mode is the default. It starts with no heat-analysis dataset and returns
HTTP 409 for analysis routes until a validated analysis dataset exists. This is
intentional: retrieved evidence is not silently converted into predictions.

Demo Mode is activated explicitly through the Data Sources dialog. It is marked
`mode: demo` and its synthetic metadata is retained. For automated tests only,
`HEATWISE_DEMO_MODE=1` enables the same labelled demonstration workflow.

## Evidence provenance

Every ingestion route persists an entry in `data_assets` with source, category,
retrieval time, observation time when available, coverage, resolution, units,
processing/quality notes, freshness status, mode, and `analysis_ready: false`.
It is intentionally not a model input in Phase 1.

## Migrations

`backend/app/migrations.py` is an append-only migration runner. Applied
revisions are stored in `schema_migrations`; current revisions create the
legacy analysis tables and the normalized `data_assets` table. Startup calls
`init_db()`, which applies only unapplied revisions and never drops data.

To inspect the active revision locally, call `GET /api/health` and read
`schema_revision`.
