"""Phase 1 contract tests: truthful startup, provenance, and migration state."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import assets, init_db, save_asset
from app.migrations import current_revision
from app.provenance import provenance
from app.services.state import clear_state, state


def test_normal_mode_does_not_lazy_seed_demo_data(monkeypatch):
    """A persisted demo dataset cannot silently become normal-mode analysis."""
    init_db()
    clear_state("Delhi")
    monkeypatch.delenv("HEATWISE_DEMO_MODE", raising=False)
    with pytest.raises(HTTPException) as error:
        state("Delhi")
    assert error.value.status_code == 409


def test_evidence_assets_have_standardized_provenance():
    init_db()
    meta = provenance(
        source="Test source",
        category="weather",
        city="Ahmedabad",
        observation_time="2026-01-01T00:00:00Z",
        resolution="point",
        units={"temperature": "°C"},
    )
    identifier = save_asset("weather", {"value": 31.2}, meta)
    asset = next(item for item in assets(city="Ahmedabad") if item["id"] == identifier)
    assert asset["analysis_ready"] is False
    assert asset["provenance"]["retrieved_at"]
    assert asset["provenance"]["mode"] == "live"


def test_schema_migrations_are_recorded():
    init_db()
    assert current_revision() == "0002_provenance_assets"


def test_normal_mode_api_returns_a_truthful_no_analysis_state(monkeypatch):
    from app.main import app

    monkeypatch.delenv("HEATWISE_DEMO_MODE", raising=False)
    clear_state("Hyderabad")
    with TestClient(app) as client:
        health = client.get("/api/health")
        overview = client.get("/api/overview?city=Hyderabad")
    assert health.status_code == 200
    assert health.json()["mode"] == "normal"
    assert overview.status_code == 409
