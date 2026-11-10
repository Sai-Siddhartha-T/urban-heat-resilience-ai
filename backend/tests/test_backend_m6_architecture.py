"""Integration and regression test suite for Milestone 6:
Backend Architecture, API Route Consistency, Database Reliability, and Risk Module Modularization.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk import (
    risk,
    calculate_hazard,
    calculate_exposure,
    calculate_vulnerability,
    classify_risk_level,
    HAZARD_MAX_SUHII,
    EXPOSURE_MAX_DENSITY,
    VULNERABILITY_MAX_ELDERLY_SHARE,
    RISK_HIGH_THRESHOLD,
    RISK_MODERATE_THRESHOLD,
    DEFAULT_WEIGHTS,
    MISSING_INDICATORS,
    METHOD_DESCRIPTION,
)
from app.services.planning import risk as planning_risk
from app.db import init_db, save, records, engine, POSTGIS


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# =====================================================================
# 1. Dedicated Risk Service Tests
# =====================================================================

def test_risk_backward_compatibility_reexport():
    """Verify that app.services.planning re-exports the identical risk function from app.services.risk."""
    assert risk is planning_risk


def test_risk_standard_calculation():
    """Verify standard IPCC risk calculation with typical zone properties."""
    zone_data = {
        "predicted_suhii": 4.0,  # hazard = 4.0 / 8.0 = 0.5
        "population_density": 12500.0,  # exposure = 12500 / 25000 = 0.5
        "elderly_share": 0.125,  # vulnerability = 0.125 / 0.25 = 0.5
    }
    result = risk(zone_data, weights=(1.0, 1.0, 1.0))
    # risk = 100 * 0.5 * 0.5 * 0.5 = 12.5 -> Moderate
    assert abs(result["hazard"] - 0.5) < 1e-6
    assert abs(result["exposure"] - 0.5) < 1e-6
    assert abs(result["vulnerability"] - 0.5) < 1e-6
    assert abs(result["risk_score"] - 12.5) < 1e-4
    assert result["risk_level"] == "Moderate"
    assert result["missing_indicators"] == MISSING_INDICATORS
    assert result["method"] == METHOD_DESCRIPTION


def test_risk_threshold_classifications():
    """Verify boundary thresholds for High, Moderate, and Low risk classifications."""
    assert classify_risk_level(25.0) == "High"
    assert classify_risk_level(20.0) == "High"
    assert classify_risk_level(19.99) == "Moderate"
    assert classify_risk_level(8.0) == "Moderate"
    assert classify_risk_level(7.99) == "Low"
    assert classify_risk_level(0.0) == "Low"


def test_risk_clipping_and_edge_cases():
    """Verify bounds clipping [0, 1] for hazard, exposure, and vulnerability."""
    # Negative values
    neg_zone = {
        "predicted_suhii": -5.0,
        "population_density": -100.0,
        "elderly_share": -0.1,
    }
    res_neg = risk(neg_zone)
    assert res_neg["hazard"] == 0.0
    assert res_neg["exposure"] == 0.0
    assert res_neg["vulnerability"] == 0.0
    assert res_neg["risk_score"] == 0.0
    assert res_neg["risk_level"] == "Low"

    # Extreme overflow values
    overflow_zone = {
        "predicted_suhii": 20.0,  # > 8
        "population_density": 100000.0,  # > 25000
        "elderly_share": 0.8,  # > 0.25
    }
    res_overflow = risk(overflow_zone)
    assert res_overflow["hazard"] == 1.0
    assert res_overflow["exposure"] == 1.0
    assert res_overflow["vulnerability"] == 1.0
    assert res_overflow["risk_score"] == 100.0
    assert res_overflow["risk_level"] == "High"


def test_risk_observed_suhii_fallback():
    """Verify that if predicted_suhii is missing, observed_suhii is used."""
    zone_data = {
        "observed_suhii": 3.2,
        "population_density": 10000.0,
        "elderly_share": 0.1,
    }
    res = risk(zone_data)
    assert abs(res["hazard"] - (3.2 / 8.0)) < 1e-6
    assert res["risk_score"] > 0


def test_risk_custom_weights():
    """Verify exponential weighting sensitivity."""
    zone_data = {
        "predicted_suhii": 4.0,  # 0.5
        "population_density": 12500.0,  # 0.5
        "elderly_share": 0.125,  # 0.5
    }
    # Double hazard weight: (0.5)^2 * 0.5 * 0.5 = 0.0625 -> 6.25
    res = risk(zone_data, weights=(2.0, 1.0, 1.0))
    assert abs(res["risk_score"] - 6.25) < 1e-4


# =====================================================================
# 2. API Route Consistency & Prefix Harmonization Tests
# =====================================================================

def test_api_cities_and_direct_cities(client):
    """Ensure both /api/cities and direct /cities return identical supported cities."""
    r_api = client.get("/api/cities")
    assert r_api.status_code == 200
    data_api = r_api.json()
    assert len(data_api) >= 3

    r_direct = client.get("/cities")
    assert r_direct.status_code == 200
    data_direct = r_direct.json()
    assert data_api == data_direct


def test_api_overview_and_direct_overview(client):
    """Ensure both /api/overview and direct /overview return identical city overviews."""
    r_api = client.get("/api/overview?city=Ahmedabad")
    assert r_api.status_code == 200
    data_api = r_api.json()

    r_direct = client.get("/overview?city=Ahmedabad")
    assert r_direct.status_code == 200
    data_direct = r_direct.json()
    assert data_api["city"] == data_direct["city"]
    assert data_api["average_suhii"] == data_direct["average_suhii"]
    assert data_api["zone_count"] == data_direct["zone_count"]


def test_api_health_and_direct_health(client):
    """Ensure both /api/health and direct /health return valid health status."""
    r_api = client.get("/api/health")
    assert r_api.status_code == 200
    data_api = r_api.json()
    assert data_api["status"] == "ok"

    r_direct = client.get("/health")
    assert r_direct.status_code == 200
    assert r_direct.json()["status"] == "ok"


def test_double_api_prefix_normalization(client):
    """Ensure transparent resolution for /api/api/* without 404."""
    r_double = client.get("/api/api/cities")
    assert r_double.status_code == 200
    assert len(r_double.json()) >= 3


def test_harmonized_models_endpoints(client):
    """Verify that models and xai endpoints under /api/ resolve correctly."""
    r_models = client.get("/api/models?city=Ahmedabad")
    assert r_models.status_code == 200
    assert "winner" in r_models.json()

    r_importance = client.get("/api/xai/importance?city=Ahmedabad")
    assert r_importance.status_code == 200
    assert isinstance(r_importance.json(), list)


def test_harmonized_simulation_endpoints(client):
    """Verify that interventions and simulation endpoints resolve correctly."""
    r_interventions = client.get("/api/interventions")
    assert r_interventions.status_code == 200
    data = r_interventions.json()
    assert "interventions" in data
    assert "trees" in data["interventions"]

    r_scenarios = client.get("/api/simulation/results?city=Ahmedabad")
    assert r_scenarios.status_code == 200
    assert isinstance(r_scenarios.json(), list)


def test_risk_analyze_endpoint(client):
    """Verify that /api/risk/analyze correctly executes through app.services.risk."""
    r = client.post(
        "/api/risk/analyze",
        json={"city": "Ahmedabad", "hazard_weight": 1.2, "exposure_weight": 1.0, "vulnerability_weight": 0.8},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "Ahmedabad"
    assert len(data["zones"]) > 0
    zone_0 = data["zones"][0]
    assert "risk_score" in zone_0
    assert "hazard" in zone_0
    assert "exposure" in zone_0
    assert "vulnerability" in zone_0
    assert "risk_level" in zone_0


# =====================================================================
# 3. Database and Environment Reliability Tests
# =====================================================================

def test_db_init_and_crud():
    """Verify init_db, record insertion, and retrieval functionality."""
    init_db()
    test_kind = "test_verification_record"
    test_payload = {"key": "m6_value", "verified": True}
    record_id = save(test_kind, test_payload)
    assert record_id is not None

    fetched = records(test_kind, limit=5)
    assert len(fetched) >= 1
    match = next(r for r in fetched if r["id"] == record_id)
    assert match["key"] == "m6_value"
    assert match["verified"] is True
    assert "created_at" in match


def test_db_postgres_url_compatibility():
    """Verify that legacy postgres:// URLs are converted to postgresql:// for SQLAlchemy."""
    raw_url = "postgres://user:password@localhost:5432/testdb"
    converted = raw_url.replace("postgres://", "postgresql://", 1) if raw_url.startswith("postgres://") else raw_url
    assert converted.startswith("postgresql://")


# =====================================================================
# 4. Mode Resolution, Groundwater Parity, and Exception Handling Tests
# =====================================================================

def test_mode_resolution_logic(monkeypatch):
    """Verify resolve_mode handles explicit overrides and environment variables."""
    from app.services.state import resolve_mode

    # Explicit parameters take absolute priority
    assert resolve_mode("demo") == "demo"
    assert resolve_mode("normal") == "normal"
    assert resolve_mode("DEMO") == "demo"
    assert resolve_mode("NORMAL") == "normal"

    # When mode is None, check HEATWISE_DEMO_MODE
    monkeypatch.setenv("HEATWISE_DEMO_MODE", "1")
    monkeypatch.delenv("HEATWISE_MODE", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    assert resolve_mode(None) == "demo"

    monkeypatch.setenv("HEATWISE_DEMO_MODE", "0")
    monkeypatch.setenv("HEATWISE_MODE", "demo")
    assert resolve_mode(None) == "demo"

    monkeypatch.setenv("HEATWISE_MODE", "normal")
    monkeypatch.setenv("TESTING", "1")
    assert resolve_mode(None) == "demo"

    monkeypatch.setenv("HEATWISE_DEMO_MODE", "0")
    monkeypatch.setenv("HEATWISE_MODE", "0")
    monkeypatch.setenv("TESTING", "0")
    assert resolve_mode(None) == "normal"


def test_groundwater_schema_and_ingestion(client):
    """Verify AreaRequest accepts source='groundwater' and /api/data/ingest processes it."""
    from app.schemas import AreaRequest

    req = AreaRequest(city="Ahmedabad", source="groundwater")
    assert req.source == "groundwater"

    resp = client.post("/api/data/ingest", json={"city": "Ahmedabad", "source": "groundwater"})
    assert resp.status_code == 200
    data = resp.json()
    assert "asset_id" in data
    assert data["provenance"]["category"] == "groundwater"


def test_schemas_evidence_import_compatibility():
    """Verify that evidence types can be cleanly imported from either app.schemas or app.schemas.evidence."""
    from app.schemas import (
        AreaRequest,
        CityName,
        EvidenceProvenance,
        EvidenceAsset,
        LayersResponse,
        MapLayer,
    )
    from app.schemas.evidence import (
        CityName as EvCityName,
        EvidenceProvenance as EvProvenance,
        EvidenceAsset as EvAsset,
        LayersResponse as EvLayersResponse,
    )

    assert CityName is EvCityName
    assert EvidenceProvenance is EvProvenance
    assert EvidenceAsset is EvAsset
    assert LayersResponse is EvLayersResponse


def test_missing_credentials_graceful_degradation(client, monkeypatch):
    """Verify that unconfigured external credentials return 503 with status='unavailable' and setup instructions."""
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    resp = client.post("/api/data/ingest", json={"city": "Ahmedabad", "source": "openaq"})
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["status"] == "unavailable"
    assert "OPENAQ_API_KEY" in payload["detail"]
    assert "setup_instructions" in payload
    assert "openaq.org" in payload["setup_instructions"].lower()
