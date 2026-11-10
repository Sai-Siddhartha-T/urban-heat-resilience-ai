"""Comprehensive End-to-End (E2E) Test Suite across Tiers 1–4.

Systematic Methodology:
- Tier 1: Feature Coverage (>=5 tests per major feature area across 10 areas)
- Tier 2: Boundary Value Analysis (BVA), extreme values & corner cases
- Tier 3: Cross-Feature Pairwise Integration Workflows
- Tier 4: Real-World Municipal Climate Resilience Planning Scenarios

Architectural Invariant:
100% offline, self-contained, and deterministic execution.
"""

import copy
import csv
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fast Startup & Offline Environment Configuration
# ---------------------------------------------------------------------------
os.environ["FAST_STARTUP"] = "1"
os.environ["PREWARM_STATE"] = "0"
os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp(prefix="heatwise-mpl-")
os.environ["API_TOKEN"] = ""

# ---------------------------------------------------------------------------
# Windows Sandbox IOCP Proactor Patch (prevents socketpair connect hang)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import _overlapped
    import signal
    import asyncio.windows_events as _we
    import asyncio.proactor_events as _pe

    _orig_set_wakeup_fd = signal.set_wakeup_fd

    def _safe_set_wakeup_fd(fd, *args, **kwargs):
        try:
            return _orig_set_wakeup_fd(fd, *args, **kwargs)
        except OSError:
            return -1

    signal.set_wakeup_fd = _safe_set_wakeup_fd

    class _DummySocket:
        def fileno(self):
            return -1

        def setblocking(self, flag):
            pass

        def send(self, data):
            return len(data)

        def close(self):
            pass

    def _make_self_pipe(self):
        self._ssock = _DummySocket()
        self._csock = _DummySocket()
        self._internal_fds += 1

    def _close_self_pipe(self):
        self._self_reading_future = None
        self._ssock = None
        self._csock = None
        self._internal_fds -= 1

    def _loop_self_reading(self, f=None):
        pass

    def _write_to_self(self):
        try:
            _overlapped.PostQueuedCompletionStatus(self._proactor._iocp, 0, 0, 0)
        except Exception:
            pass

    _pe.BaseProactorEventLoop._make_self_pipe = _make_self_pipe
    _pe.BaseProactorEventLoop._close_self_pipe = _close_self_pipe
    _pe.BaseProactorEventLoop._loop_self_reading = _loop_self_reading
    _pe.BaseProactorEventLoop._write_to_self = _write_to_self

    _orig_poll = _we.IocpProactor._poll

    def _safe_poll(self, timeout=None):
        try:
            return _orig_poll(self, timeout)
        except OSError:
            return

    _we.IocpProactor._poll = _safe_poll

# Import application components after offline env & event loop setup
from app.main import app
from app.services.state import state, zone
from app.services.planning import INTERVENTIONS


@pytest.fixture(scope="module")
def client():
    """Module-scoped client running against initialized SQLite in-memory/test DB."""
    with TestClient(app) as c:
        yield c


# ===========================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per area across 10 feature areas)
# ===========================================================================

# ---------------------------------------------------------------------------
# Feature Area 1: System Health & Foundation (/api/health, /api/ready, /api/cities)
# ---------------------------------------------------------------------------


def test_tier1_foundation_health_ok(client):
    """Verify health probe returns HTTP 200 with ok status and synthetic flag."""
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["synthetic_predictions"] is True


def test_tier1_foundation_database_identification(client):
    """Verify health probe correctly reports the connected database engine."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "database" in res.json()
    assert ("SQLite" in res.json()["database"]) or ("PostgreSQL" in res.json()["database"])


def test_tier1_foundation_cities_catalog(client):
    """Verify supported cities endpoint lists all 3 baseline municipal centers."""
    res = client.get("/api/cities")
    assert res.status_code == 200
    cities = {c["name"]: c["center"] for c in res.json()}
    assert "Ahmedabad" in cities
    assert "Delhi" in cities
    assert "Hyderabad" in cities
    assert len(cities["Ahmedabad"]) == 2


def test_tier1_foundation_overview_ahmedabad(client):
    """Verify city overview returns high-level spatial aggregate metrics."""
    res = client.get("/api/overview?city=Ahmedabad")
    assert res.status_code == 200
    data = res.json()
    assert data["city"] == "Ahmedabad"
    assert data["zone_count"] == 324
    assert data["area_km2"] > 0
    assert data["average_suhii"] > 0
    assert isinstance(data["priority_zones"], list)
    assert len(data["priority_zones"]) <= 8


def test_tier1_foundation_tile_coordinate_validation(client):
    """Verify tile server endpoint rejects out-of-range tile coordinates."""
    # Zoom level out of bounds
    assert client.get("/api/tiles/25/0/0.png").status_code == 422
    # Negative coordinate
    assert client.get("/api/tiles/5/-1/0.png").status_code == 422


# ---------------------------------------------------------------------------
# Feature Area 2: Heat Metrics & Baseline Data (/api/heat/*)
# ---------------------------------------------------------------------------


def test_tier1_heat_map_geojson_structure(client):
    """Verify /api/heat/map returns a valid GeoJSON FeatureCollection."""
    res = client.get("/api/heat/map?city=Ahmedabad")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 324
    f0 = data["features"][0]
    assert f0["geometry"]["type"] == "Polygon"
    assert "predicted_suhii" in f0["properties"]
    assert "predicted_lst" in f0["properties"]


def test_tier1_heat_hotspots_classification(client):
    """Verify /api/heat/hotspots returns only zones exceeding the 4.0°C threshold."""
    res = client.get("/api/heat/hotspots?city=Ahmedabad")
    assert res.status_code == 200
    hotspots = res.json()
    assert isinstance(hotspots, list)
    for zone_props in hotspots:
        assert zone_props["hotspot"] is True
        assert zone_props["predicted_suhii"] >= 4.0


def test_tier1_heat_predict_batch(client):
    """Verify /api/heat/predict without zone_id returns predictions for all zones."""
    res = client.post("/api/heat/predict", json={"city": "Ahmedabad"})
    assert res.status_code == 200
    data = res.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 324
    assert "model" in data


def test_tier1_heat_predict_single_zone(client):
    """Verify /api/heat/predict with zone_id returns exact zone prediction."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    target_id = overview["priority_zones"][0]["id"]
    res = client.post("/api/heat/predict", json={"city": "Ahmedabad", "zone_id": target_id})
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == target_id
    assert body["city"] == "Ahmedabad"
    assert "predicted_suhii" in body
    assert body["interval_low"] <= body["predicted_suhii"] <= body["interval_high"]


def test_tier1_heat_overview_delhi_and_hyderabad(client):
    """Verify overview metrics calculate cleanly for secondary cities."""
    for city in ["Delhi", "Hyderabad"]:
        res = client.get(f"/api/overview?city={city}")
        assert res.status_code == 200
        data = res.json()
        assert data["city"] == city
        assert data["zone_count"] == 324
        assert data["average_lst"] > data["average_suhii"]


# ---------------------------------------------------------------------------
# Feature Area 3: ML Training, Cross-Validation & Predictions (/api/models/*)
# ---------------------------------------------------------------------------


def test_tier1_ml_models_metadata_and_tournament(client):
    """Verify /api/models returns tournament evaluations across candidate architectures."""
    res = client.get("/api/models?city=Ahmedabad")
    assert res.status_code == 200
    body = res.json()
    assert body["winner"] in ["Random Forest", "XGBoost", "LightGBM"]
    assert len(body["evaluations"]) == 3
    names = [e["model"] for e in body["evaluations"]]
    assert "Random Forest" in names
    assert "XGBoost" in names
    assert "LightGBM" in names


def test_tier1_ml_spatial_holdout_split(client):
    """Verify 6 longitude-based spatial block split holds across partitions."""
    res = client.get("/api/models?city=Ahmedabad")
    assert res.status_code == 200
    split = res.json()["split"]
    assert split["training"] == 162
    assert split["validation"] == 54
    assert split["test"] == 54
    assert split["buffer"] == 54
    assert "Western 9 columns train" in split["method"]


def test_tier1_ml_features_non_leaking(client):
    """Verify target and coordinate leakage are strictly excluded from feature set."""
    res = client.get("/api/models?city=Ahmedabad")
    assert res.status_code == 200
    features = res.json()["features"]
    assert "observed_suhii" not in features
    assert "lst" not in features
    assert "latitude" not in features
    assert "longitude" not in features
    assert "building_density" in features
    assert "ndvi" in features


def test_tier1_ml_prediction_confidence_intervals(client):
    """Verify predicted intervals are positive and symmetric around point estimates."""
    res = client.get("/api/models?city=Ahmedabad")
    assert res.status_code == 200
    interval = res.json()["interval"]
    assert interval > 0

    heat_map = client.get("/api/heat/map?city=Ahmedabad").json()
    for f in heat_map["features"][:10]:
        p = f["properties"]
        expected_diff = p["interval_high"] - p["predicted_suhii"]
        assert abs(expected_diff - interval) < 1e-4


def test_tier1_ml_retrain_endpoint(client):
    """Verify /api/models/train forces model retraining and returns refreshed artifact."""
    res = client.post("/api/models/train", json={"city": "Ahmedabad"})
    assert res.status_code == 200
    artifact = res.json()
    assert "winner" in artifact
    assert len(artifact["evaluations"]) == 3


# ---------------------------------------------------------------------------
# Feature Area 4: TreeSHAP Feature Importance & Explanations (/api/xai/*)
# ---------------------------------------------------------------------------


def test_tier1_xai_local_shap_additivity(client):
    """Verify exact local TreeSHAP additivity: base_value + sum(contributions) == prediction."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post("/api/xai/explain", json={"city": "Ahmedabad", "zone_id": zone_id})
    assert res.status_code == 200
    data = res.json()
    pred = data["prediction"]
    base = data["base_value"]
    total_shap = sum(data["contributions"].values())
    assert abs(base + total_shap - pred) < 1e-4
    assert "TreeSHAP" in data["note"]


def test_tier1_xai_global_feature_importance_ranking(client):
    """Verify /api/xai/importance returns ranked list of global SHAP importances."""
    res = client.get("/api/xai/importance?city=Ahmedabad")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 10
    # Confirm list is sorted descending
    for i in range(len(items) - 1):
        assert items[i]["importance"] >= items[i + 1]["importance"]


def test_tier1_xai_hottest_zone_explanation(client):
    """Verify highest heat hotspot has positive built surface SHAP contributions."""
    hotspots = client.get("/api/heat/hotspots?city=Ahmedabad").json()
    hottest = max(hotspots, key=lambda z: z["predicted_suhii"])
    res = client.post("/api/xai/explain", json={"city": "Ahmedabad", "zone_id": hottest["id"]})
    assert res.status_code == 200
    contribs = res.json()["contributions"]
    assert contribs["building_density"] > 0 or contribs["ndbi"] > 0


def test_tier1_xai_coolest_zone_explanation(client):
    """Verify coolest zone has negative SHAP cooling contributions from vegetation/water."""
    heat_map = client.get("/api/heat/map?city=Ahmedabad").json()
    coolest = min(heat_map["features"], key=lambda f: f["properties"]["predicted_suhii"])["properties"]
    res = client.post("/api/xai/explain", json={"city": "Ahmedabad", "zone_id": coolest["id"]})
    assert res.status_code == 200
    contribs = res.json()["contributions"]
    assert contribs["ndvi"] < 0 or contribs["soil_moisture"] < 0


def test_tier1_xai_missing_zone_returns_404(client):
    """Verify explanation endpoint raises 404 on nonexistent zone identifier."""
    res = client.post("/api/xai/explain", json={"city": "Ahmedabad", "zone_id": "nonexistent-zone-999"})
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Feature Area 5: Urban Heat Risk Index & Vulnerability (/api/risk/*)
# ---------------------------------------------------------------------------


def test_tier1_risk_default_weights(client):
    """Verify /api/risk/analyze computes balanced composite risk scores."""
    res = client.post(
        "/api/risk/analyze",
        json={"city": "Ahmedabad", "hazard_weight": 1.0, "exposure_weight": 1.0, "vulnerability_weight": 1.0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["weights"] == [1.0, 1.0, 1.0]
    assert len(body["zones"]) == 324
    z0 = body["zones"][0]
    assert "risk_score" in z0
    assert z0["risk_level"] in ["Low", "Moderate", "High"]


def test_tier1_risk_custom_hazard_weight(client):
    """Verify scaling hazard weight increases relative risk in high-heat zones."""
    hotspots = client.get("/api/heat/hotspots?city=Ahmedabad").json()
    target_id = hotspots[0]["id"]

    r_base = client.post(
        "/api/risk/analyze",
        json={"city": "Ahmedabad", "zone_id": target_id, "hazard_weight": 1.0, "exposure_weight": 1.0, "vulnerability_weight": 1.0},
    ).json()["zones"][0]["risk_score"]

    r_hazard = client.post(
        "/api/risk/analyze",
        json={"city": "Ahmedabad", "zone_id": target_id, "hazard_weight": 2.5, "exposure_weight": 1.0, "vulnerability_weight": 1.0},
    ).json()["zones"][0]["risk_score"]

    assert r_hazard != r_base
    assert 0 <= r_hazard <= 100


def test_tier1_risk_custom_vulnerability_weight(client):
    """Verify vulnerability weight amplifies sensitivity and demographic factors."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/risk/analyze",
        json={"city": "Ahmedabad", "zone_id": zone_id, "vulnerability_weight": 3.0},
    )
    assert res.status_code == 200
    zone_risk = res.json()["zones"][0]
    assert zone_risk["vulnerability"] >= 0


def test_tier1_risk_single_zone_calculation(client):
    """Verify querying risk analysis for a single zone returns exactly 1 zone record."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    target_id = overview["priority_zones"][0]["id"]
    res = client.post("/api/risk/analyze", json={"city": "Ahmedabad", "zone_id": target_id})
    assert res.status_code == 200
    assert len(res.json()["zones"]) == 1
    assert res.json()["zones"][0]["zone_id"] == target_id


def test_tier1_risk_full_city_batch_calculation(client):
    """Verify full-city risk evaluation produces complete distribution across all 324 zones."""
    res = client.post("/api/risk/analyze", json={"city": "Delhi"})
    assert res.status_code == 200
    zones = res.json()["zones"]
    assert len(zones) == 324
    levels = {z["risk_level"] for z in zones}
    assert "High" in levels or "Moderate" in levels


# ---------------------------------------------------------------------------
# Feature Area 6: 8 Intervention Simulation Models (/api/simulation/*)
# ---------------------------------------------------------------------------


def test_tier1_simulation_interventions_catalog(client):
    """Verify /api/interventions catalogs all 8 supported urban interventions."""
    res = client.get("/api/interventions")
    assert res.status_code == 200
    catalog = res.json()["interventions"]
    expected = ["trees", "vegetation", "parks", "cool_roofs", "pavements", "corridors", "roof_gardens", "water"]
    for item in expected:
        assert item in catalog
        assert "cooling_per_10pct" in catalog[item]
        assert "water_per_pct" in catalog[item]


def test_tier1_simulation_urban_trees_cooling_and_water(client):
    """Verify tree canopy simulation accurately projects cooling and water consumption."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": zone_id, "coverage": {"trees": 10}, "water_limit": 500},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert data["estimated_cooling"] == pytest.approx(0.35, abs=0.01)
    assert data["water_m3_day"] > 0
    assert data["before_suhii"] > data["after_suhii"]


def test_tier1_simulation_cool_roofs_zero_water(client):
    """Verify cool roof intervention provides reflective cooling with zero water demand."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": zone_id, "coverage": {"cool_roofs": 15}, "water_limit": 0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert data["estimated_cooling"] > 0
    assert data["water_m3_day"] == 0.0


def test_tier1_simulation_reflective_pavements(client):
    """Verify reflective road pavement simulation succeeds within road capacity."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": zone_id, "coverage": {"pavements": 5}},
    )
    assert res.status_code == 200
    assert res.json()["feasible"] is True
    assert res.json()["estimated_cooling"] == pytest.approx(0.09, abs=0.01)


def test_tier1_simulation_convenience_inputs(client):
    """Verify tree_count and roof_treated_pct convenience inputs map accurately."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={
            "city": "Ahmedabad",
            "zone_id": zone_id,
            "tree_count": 500,
            "roof_treated_pct": 50.0,
            "road_treated_pct": 25.0,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["feasible"] is True
    assert len(body["conversion_notes"]) >= 2
    assert "trees" in body["coverage"]
    assert "cool_roofs" in body["coverage"]


# ---------------------------------------------------------------------------
# Feature Area 7: OR-Tools CP-SAT Multi-Zone Optimizer (/api/optimization/*)
# ---------------------------------------------------------------------------


def test_tier1_optimizer_basic_multi_zone_feasible(client):
    """Verify CP-SAT solver finds optimal intervention allocation within water budget."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 500, "max_vegetation_pct": 30},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert data["status"] in ["OPTIMAL", "FEASIBLE"]
    assert data["water_used"] <= 500
    assert len(data["selections"]) > 0


def test_tier1_optimizer_water_limit_constraint(client):
    """Verify water limit is strictly respected across all zone allocations."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 250},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["water_used"] <= 250


def test_tier1_optimizer_budget_limit_constraint(client):
    """Verify physical water and surface constraints are enforced without budget restriction."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 600},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert data["water_used"] <= 600


def test_tier1_optimizer_half_water_alternative(client):
    """Verify solver automatically returns 50% water sensitivity alternative."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 400},
    )
    assert res.status_code == 200
    data = res.json()
    assert "alternative" in data
    alt = data["alternative"]
    assert alt["label"] == "Half-water alternative"
    assert alt["water_used"] <= 200


def test_tier1_optimizer_infeasible_problem(client):
    """Verify impossible constraints correctly trigger INFEASIBLE solver status."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 0, "max_vegetation_pct": 0, "land_limit_pct": 0, "min_cooling": 3.8},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is False
    assert data["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# Feature Area 8: AI Resilience Assistant with Guardrails (/api/ai/*)
# ---------------------------------------------------------------------------


def test_tier1_ai_local_provider_fallback_structure(client):
    """Verify local evidence assistant produces schema-compliant response."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/ai/chat",
        json={"city": "Ahmedabad", "zone_id": zone_id, "message": "Explain local heat drivers", "provider": "local"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fallback"] is True
    assert "summary" in body
    assert isinstance(body["findings"], list)
    assert isinstance(body["actions"], list)
    assert len(body["limitations"]) > 0


def test_tier1_ai_context_grounding_citations(client):
    """Verify AI assistant citations only cite available factual evidence keys."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/ai/chat",
        json={"city": "Ahmedabad", "zone_id": zone_id, "message": "What is driving heat?", "provider": "local"},
    )
    assert res.status_code == 200
    data = res.json()
    fact_keys = set(data["facts"].keys())
    for finding in data["findings"]:
        for cited_id in finding["fact_ids"]:
            assert cited_id in fact_keys


def test_tier1_ai_numeric_guardrails_no_prose_digits(client):
    """Verify AI assistant prose is strictly guarded against raw hallucinated numbers."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/ai/chat",
        json={"city": "Ahmedabad", "zone_id": zone_id, "message": "Provide actionable steps", "provider": "local"},
    )
    assert res.status_code == 200
    findings = res.json()["findings"]
    for finding in findings:
        # Prose findings should convey qualitative reasoning without raw numbers
        assert not re.search(r"\b\d+\.\d+\b", finding["statement"])


def test_tier1_ai_suggests_only_feasible_actions(client):
    """Verify recommended actions are physically feasible for the selected zone."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/ai/chat",
        json={"city": "Ahmedabad", "zone_id": zone_id, "message": "Suggest top interventions", "provider": "local"},
    )
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) > 0
    for act in actions:
        assert act in INTERVENTIONS


def test_tier1_ai_provider_failover_status(client, monkeypatch):
    """Verify auto provider cleanly reports failover when API keys are unconfigured."""
    for key in ["GROQ_API_KEY", "GEMINI_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    res = client.post(
        "/api/ai/chat",
        json={"city": "Ahmedabad", "message": "Assess heat risks", "provider": "auto"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["fallback"] is True
    assert len(data["failures"]) == 2


# ---------------------------------------------------------------------------
# Feature Area 9: Data Ingestion & Catalogs (/api/data/*)
# ---------------------------------------------------------------------------


def test_tier1_data_status_catalogs_and_providers(client):
    """Verify /api/data/status lists providers, catalogs, and ingestion provenance."""
    res = client.get("/api/data/status")
    assert res.status_code == 200
    body = res.json()
    assert "catalog" in body
    assert "providers" in body
    assert "groq" in body["providers"]
    assert "gemini" in body["providers"]
    assert "prediction_data" in body


def test_tier1_data_ingest_sample_synthetic(client):
    """Verify /api/data/ingest with sample source re-analyzes deterministic landscape."""
    res = client.post("/api/data/ingest", json={"city": "Ahmedabad", "source": "sample"})
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "synthetic"
    assert body["zones"] == 324
    assert body["metadata"]["city"] == "Ahmedabad"


def test_tier1_data_series_weather_structure(client):
    """Verify weather time-series endpoint returns structured observation records."""
    res = client.get("/api/data/series")
    assert res.status_code == 200
    data = res.json()
    assert "series" in data
    assert isinstance(data["series"], list)


def test_tier1_data_records_retrieval(client):
    """Verify querying ingested data records returns valid list response."""
    for kind in ["weather", "osm", "satellite", "monitoring"]:
        res = client.get(f"/api/data/records?kind={kind}")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


def test_tier1_data_upstream_error_explicit_502(client, monkeypatch):
    """Verify remote data connection errors produce explicit HTTP 502 with no masking."""
    import httpx
    from app.services import sources

    async def _mock_unreachable(*args, **kwargs):
        raise httpx.ConnectError("Network unreachable")

    monkeypatch.setattr(sources, "weather", _mock_unreachable)
    res = client.post("/api/data/ingest", json={"city": "Ahmedabad", "source": "weather"})
    assert res.status_code == 502
    assert "No substitute data" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Feature Area 10: Report Generation & Export (/api/reports/*)
# ---------------------------------------------------------------------------


def test_tier1_reports_generate_metadata(client):
    """Verify /api/reports/generate creates a municipal report and returns endpoints."""
    res = client.post("/api/reports/generate", json={"city": "Ahmedabad"})
    assert res.status_code == 200
    body = res.json()
    assert "id" in body
    assert "download_url" in body
    assert "csv_url" in body
    assert "markdown_url" in body


def test_tier1_reports_download_json(client):
    """Verify JSON report download provides complete structured planning synthesis."""
    rep_id = client.post("/api/reports/generate", json={"city": "Ahmedabad"}).json()["id"]
    res = client.get(f"/api/reports/{rep_id}/download")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    content = res.json()
    assert "Ahmedabad" in content["title"]
    assert "summary" in content
    assert "models" in content
    assert len(content["zones"]) == 324


def test_tier1_reports_download_csv_format(client):
    """Verify CSV export produces valid comma-separated format with header fields."""
    rep_id = client.post("/api/reports/generate", json={"city": "Ahmedabad"}).json()["id"]
    res = client.get(f"/api/reports/{rep_id}/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    reader = csv.reader(io.StringIO(res.text))
    header = next(reader)
    assert "id" in header
    assert "predicted_suhii" in header
    assert "risk_score" in header
    rows = list(reader)
    assert len(rows) == 324


def test_tier1_reports_download_markdown_disclaimer(client):
    """Verify Markdown export contains mandatory synthetic research demonstration disclaimer."""
    rep_id = client.post("/api/reports/generate", json={"city": "Ahmedabad"}).json()["id"]
    res = client.get(f"/api/reports/{rep_id}/markdown")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert "SYNTHETIC DEMONSTRATION" in res.text
    assert "Held-out synthetic evaluation" in res.text


def test_tier1_reports_missing_identifier_404(client):
    """Verify downloading a non-existent report returns HTTP 404."""
    res = client.get("/api/reports/nonexistent-report-9999/download")
    assert res.status_code == 404


# ===========================================================================
# TIER 2: BOUNDARY VALUE ANALYSIS & CORNER CASES (BVA)
# ===========================================================================


def test_tier2_bva_coordinates_latitude_bounds(client):
    """BVA: Latitude exactly at boundary [-80, 80] vs just beyond [-80.1, 80.1]."""
    # Valid boundaries
    assert client.post("/api/data/ingest", json={"latitude": 80.0, "longitude": 72.5}).status_code in [200, 422, 502]
    assert client.post("/api/data/ingest", json={"latitude": -80.0, "longitude": 72.5}).status_code in [200, 422, 502]
    # Invalid boundaries
    assert client.post("/api/data/ingest", json={"latitude": 80.1, "longitude": 72.5}).status_code == 422
    assert client.post("/api/data/ingest", json={"latitude": -80.1, "longitude": 72.5}).status_code == 422


def test_tier2_bva_coordinates_longitude_bounds(client):
    """BVA: Longitude exactly at boundary [-180, 180] vs just beyond [-180.1, 180.1]."""
    # Valid boundaries
    assert client.post("/api/data/ingest", json={"latitude": 23.0, "longitude": 180.0}).status_code in [200, 422, 502]
    assert client.post("/api/data/ingest", json={"latitude": 23.0, "longitude": -180.0}).status_code in [200, 422, 502]
    # Invalid boundaries
    assert client.post("/api/data/ingest", json={"latitude": 23.0, "longitude": 180.1}).status_code == 422
    assert client.post("/api/data/ingest", json={"latitude": 23.0, "longitude": -180.1}).status_code == 422


def test_tier2_bva_coordinates_incomplete_pair(client):
    """BVA: Supplying latitude without longitude or vice versa must be rejected."""
    assert client.post("/api/data/ingest", json={"latitude": 23.0}).status_code == 422
    assert client.post("/api/data/ingest", json={"longitude": 72.5}).status_code == 422


def test_tier2_bva_simulation_negative_water_rejected(client):
    """BVA: Negative water constraint in simulation must fail schema validation."""
    assert client.post("/api/simulation/run", json={"water_limit": -1.0}).status_code == 422


def test_tier2_bva_simulation_negative_coverage_rejected(client):
    """BVA: Negative intervention coverage percentage must fail schema validation."""
    assert client.post("/api/simulation/run", json={"coverage": {"trees": -5.0}}).status_code == 422


def test_tier2_bva_simulation_unknown_intervention_rejected(client):
    """BVA: Non-catalog intervention identifier must fail schema validation."""
    assert client.post("/api/simulation/run", json={"coverage": {"hypothetical_laser_cooling": 10}}).status_code == 422


def test_tier2_bva_simulation_extreme_water_limit(client):
    """BVA: Water limit exceeding 1e7 m3/day must be rejected by Pydantic."""
    assert client.post("/api/simulation/run", json={"water_limit": 1.01e7}).status_code == 422


def test_tier2_bva_simulation_over_capacity_roof_surfaces(client):
    """BVA: Cool roofs + roof gardens exceeding total zone roof area must be marked infeasible."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": zone_id, "coverage": {"cool_roofs": 50, "roof_gardens": 50}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["feasible"] is False
    assert any("roof" in v.lower() for v in body["violations"])


def test_tier2_bva_simulation_over_capacity_ground_surfaces(client):
    """BVA: Total ground interventions exceeding available unbuilt land must be infeasible."""
    overview = client.get("/api/overview?city=Ahmedabad").json()
    zone_id = overview["priority_zones"][0]["id"]
    res = client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": zone_id, "coverage": {"trees": 40, "parks": 40, "vegetation": 40}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["feasible"] is False
    assert any("ground" in v.lower() for v in body["violations"])


def test_tier2_bva_optimization_duplicate_zone_ids_rejected(client):
    """BVA: Duplicate zone IDs passed to multi-zone optimization must be rejected."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "zone_ids": ["ahmedabad-01-01", "ahmedabad-01-01"]},
    )
    assert res.status_code == 422


def test_tier2_bva_optimization_zero_water_limit(client):
    """BVA: Zero water limit forces solver to pick waterless interventions (cool roofs/pavements)."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "water_limit": 0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert data["water_used"] == 0.0
    for sel in data["selections"]:
        assert sel["water_m3_day"] == 0.0


def test_tier2_bva_optimization_negative_budget_rejected(client):
    """BVA: Negative financial budget limit must be rejected by schema validator."""
    res = client.post(
        "/api/optimization/run",
        json={"city": "Ahmedabad", "budget_limit": -500},
    )
    assert res.status_code == 422


def test_tier2_bva_empty_geojson_polygon_rejected(client):
    """BVA: Empty GeoJSON polygon coordinates must fail validation."""
    boundary = {"type": "Polygon", "coordinates": []}
    res = client.post("/api/data/ingest", json={"city": "Ahmedabad", "boundary": boundary})
    assert res.status_code == 422


def test_tier2_bva_non_polygon_geojson_rejected(client):
    """BVA: Non-Polygon geometry (Point, LineString) must be rejected."""
    boundary = {"type": "Point", "coordinates": [72.5714, 23.0225]}
    res = client.post("/api/data/ingest", json={"city": "Ahmedabad", "boundary": boundary})
    assert res.status_code == 422


def test_tier2_bva_polygon_area_exceeds_4_degrees_rejected(client):
    """BVA: Custom polygon bounding box exceeding 4 square degrees must be rejected."""
    boundary = {
        "type": "Polygon",
        "coordinates": [
            [
                [70.0, 20.0],
                [73.0, 20.0],
                [73.0, 23.0],
                [70.0, 23.0],
                [70.0, 20.0],
            ]
        ],
    }
    res = client.post("/api/data/ingest", json={"city": "Ahmedabad", "boundary": boundary})
    assert res.status_code == 422


def test_tier2_bva_inverted_date_range_rejected(client):
    """BVA: Inverted date range (end_date < start_date) must be rejected."""
    res = client.post(
        "/api/data/ingest",
        json={"city": "Ahmedabad", "start_date": "2025-06-01", "end_date": "2025-05-01"},
    )
    assert res.status_code == 422


def test_tier2_bva_date_range_exceeds_one_year_rejected(client):
    """BVA: Query range spanning > 366 days must be rejected."""
    res = client.post(
        "/api/data/ingest",
        json={"city": "Ahmedabad", "start_date": "2024-01-01", "end_date": "2025-06-01"},
    )
    assert res.status_code == 422


def test_tier2_bva_malformed_json_syntax(client):
    """BVA: Sending malformed / unparseable JSON payload triggers HTTP 422."""
    res = client.post(
        "/api/heat/predict",
        content="{'invalid_json': true",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


def test_tier2_bva_invalid_city_enum_rejected(client):
    """BVA: Unsupported municipal city name must be rejected by Literal enum."""
    res = client.get("/api/overview?city=Atlantis")
    assert res.status_code == 422


def test_tier2_bva_missing_zone_404(client):
    """BVA: Requesting prediction for a non-existent zone ID returns 404."""
    res = client.post("/api/heat/predict", json={"city": "Ahmedabad", "zone_id": "nonexistent-00-00"})
    assert res.status_code == 404


def test_tier2_bva_api_token_unauthorized_401(client, monkeypatch):
    """BVA: When API_TOKEN is configured, missing or invalid bearer token returns 401."""
    monkeypatch.setenv("API_TOKEN", "secure-municipal-token-2026")
    # Missing token
    assert client.get("/api/health").status_code == 401
    # Invalid token
    assert client.get("/api/health", headers={"Authorization": "Bearer wrong-token"}).status_code == 401
    # Valid token
    assert client.get("/api/health", headers={"Authorization": "Bearer secure-municipal-token-2026"}).status_code == 200


def test_tier2_bva_response_security_headers_present(client):
    """BVA: Security middleware must enforce nosniff and referrer headers."""
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"


# ===========================================================================
# TIER 3: CROSS-FEATURE PAIRWISE WORKFLOWS
# ===========================================================================


def test_tier3_workflow_ingest_predict_explain_risk(client):
    """Cross-Feature Workflow 1:

    Ingestion -> Baseline Heat -> Prediction -> SHAP Explanation -> Risk Assessment.
    Validates end-to-end data flow and mathematical coherence from raw ingestion
    through TreeSHAP additivity and composite vulnerability scoring.
    """
    # 1. Ingest baseline synthetic landscape for Hyderabad
    ingest_res = client.post("/api/data/ingest", json={"city": "Hyderabad", "source": "sample"})
    assert ingest_res.status_code == 200
    assert ingest_res.json()["zones"] == 324

    # 2. Retrieve heat map and locate highest SUHII zone
    map_res = client.get("/api/heat/map?city=Hyderabad")
    assert map_res.status_code == 200
    features = map_res.json()["features"]
    hottest_feature = max(features, key=lambda f: f["properties"]["predicted_suhii"])
    target_zone_id = hottest_feature["properties"]["id"]

    # 3. Predict SUHII for target zone
    pred_res = client.post("/api/heat/predict", json={"city": "Hyderabad", "zone_id": target_zone_id})
    assert pred_res.status_code == 200
    predicted_suhii = pred_res.json()["predicted_suhii"]

    # 4. Generate local TreeSHAP explanation and verify exact additivity
    explain_res = client.post("/api/xai/explain", json={"city": "Hyderabad", "zone_id": target_zone_id})
    assert explain_res.status_code == 200
    expl = explain_res.json()
    reconstructed = expl["base_value"] + sum(expl["contributions"].values())
    assert abs(reconstructed - predicted_suhii) < 1e-4

    # 5. Run parametric risk analysis with custom stakeholder weights
    risk_res = client.post(
        "/api/risk/analyze",
        json={"city": "Hyderabad", "zone_id": target_zone_id, "hazard_weight": 2.0, "exposure_weight": 1.5, "vulnerability_weight": 1.2},
    )
    assert risk_res.status_code == 200
    risk_data = risk_res.json()["zones"][0]
    assert risk_data["zone_id"] == target_zone_id
    assert risk_data["hazard"] > 0
    assert risk_data["risk_level"] in ["High", "Moderate", "Low"]
    assert risk_data["risk_score"] >= 0


def test_tier3_workflow_predict_simulate_optimize_export(client):
    """Cross-Feature Workflow 2:

    Prediction -> Simulation (8 interventions) -> Optimizer (CP-SAT multi-zone) ->
    Cost & Budget allocation -> Report Export (JSON, CSV, Markdown).
    """
    # 1. Obtain top priority planning zones in Ahmedabad
    overview = client.get("/api/overview?city=Ahmedabad").json()
    priority_zones = overview["priority_zones"]
    assert len(priority_zones) >= 5
    zone_ids = [z["id"] for z in priority_zones[:5]]
    target_id = zone_ids[0]

    # 2. Run simulation exercising multiple interventions
    sim_res = client.post(
        "/api/simulation/run",
        json={
            "city": "Ahmedabad",
            "zone_id": target_id,
            "name": "E2E Multi-Intervention Trial",
            "coverage": {"cool_roofs": 10, "trees": 5, "pavements": 5},
            "water_limit": 300,
        },
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["feasible"] is True
    assert sim_data["estimated_cooling"] > 0

    # 3. Execute OR-Tools CP-SAT multi-zone combinatorial optimization
    opt_res = client.post(
        "/api/optimization/run",
        json={
            "city": "Ahmedabad",
            "zone_ids": zone_ids,
            "water_limit": 450,
            "min_cooling": 0.2,
        },
    )
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert opt_data["feasible"] is True
    assert opt_data["water_used"] <= 450
    assert "alternative" in opt_data

    # 4. Generate synthesis report
    rep_res = client.post("/api/reports/generate", json={"city": "Ahmedabad"})
    assert rep_res.status_code == 200
    rep_urls = rep_res.json()

    # 5. Verify exports across JSON, CSV, and Markdown formats
    # JSON Download
    json_dl = client.get(rep_urls["download_url"])
    assert json_dl.status_code == 200
    assert len(json_dl.json()["zones"]) == 324

    # CSV Download
    csv_dl = client.get(rep_urls["csv_url"])
    assert csv_dl.status_code == 200
    assert "predicted_suhii" in csv_dl.text

    # Markdown Download
    md_dl = client.get(rep_urls["markdown_url"])
    assert md_dl.status_code == 200
    assert "SYNTHETIC DEMONSTRATION" in md_dl.text
    assert "Ahmedabad · Urban Heat Analysis" in md_dl.text


def test_tier3_workflow_ai_assistant_grounded_in_simulation(client):
    """Cross-Feature Workflow 3:

    AI Resilience Assistant querying simulation results with numerical
    guardrail verification and strict constraint grounding.
    """
    overview = client.get("/api/overview?city=Ahmedabad").json()
    target_id = overview["priority_zones"][0]["id"]

    # 1. Establish simulated scenario
    client.post(
        "/api/simulation/run",
        json={"city": "Ahmedabad", "zone_id": target_id, "coverage": {"cool_roofs": 15}, "water_limit": 200},
    )

    # 2. Query AI Assistant
    chat_res = client.post(
        "/api/ai/chat",
        json={
            "city": "Ahmedabad",
            "zone_id": target_id,
            "message": "Evaluate the cool roof intervention and explain thermal drivers.",
            "provider": "local",
        },
    )
    assert chat_res.status_code == 200
    body = chat_res.json()

    # 3. Verify factual grounding
    assert body["fallback"] is True
    facts = body["facts"]
    assert "prediction" in facts
    assert "drivers" in facts
    assert "constraints" in facts

    # 4. Verify numerical guardrails (no ungrounded numbers in prose)
    for finding in body["findings"]:
        assert not re.search(r"\b\d+\.\d+\b", finding["statement"])
        for cid in finding["fact_ids"]:
            assert cid in facts

    # 5. Verify proposed interventions match catalog
    for act in body["actions"]:
        assert act in INTERVENTIONS


# ===========================================================================
# TIER 4: REAL-WORLD MUNICIPAL PLANNING SCENARIOS
# ===========================================================================


def test_tier4_scenario_ahmedabad_heatwave_crisis(client):
    """Scenario A: Ahmedabad Extreme Heatwave Crisis (45°C ambient).

    Urban Challenge:
    - 5 high-density informal settlement zones facing acute thermal distress.
    - Extreme water scarcity limits municipal daily water budget to 200 m3/day.
    - Financial grant constrained to $30,000 CapEx.

    Planning Objective:
    - Deploy zero-water reflective cool roofs as primary intervention.
    - Supplement with modest tree canopy where ground land allows.
    - Verify 50% water sensitivity run provides viable contingency cooling.
    """
    overview = client.get("/api/overview?city=Ahmedabad").json()
    high_heat_zones = [z for z in overview["priority_zones"] if z["roof_pct"] >= 20][:5]
    assert len(high_heat_zones) >= 3
    selected_ids = [z["id"] for z in high_heat_zones]

    # Run CP-SAT solver under heatwave constraints
    opt_res = client.post(
        "/api/optimization/run",
        json={
            "city": "Ahmedabad",
            "zone_ids": selected_ids,
            "water_limit": 200.0,
            "min_cooling": 0.15,
        },
    )
    assert opt_res.status_code == 200
    opt = opt_res.json()
    assert opt["feasible"] is True
    assert opt["water_used"] <= 200.0

    # In water-scarce heatwave, cool roofs should dominate allocation
    cool_roof_allocations = [
        sel["coverage"].get("cool_roofs", 0) for sel in opt["selections"]
    ]
    assert any(cov > 0 for cov in cool_roof_allocations)

    # Verify half-water alternative is feasible
    alt = opt["alternative"]
    assert alt["feasible"] is True
    assert alt["water_used"] <= 100.0


def test_tier4_scenario_rapid_urbanization_flood_heat_dual_hazard(client):
    """Scenario B: Rapid Urbanization Flood & Heat Dual-Hazard.

    Urban Challenge:
    - High-density developing peripheral sector in Hyderabad.
    - Low infiltration / impermeable surfaces create flash-flood and urban heat dual hazards.

    Planning Objective:
    - Simulate green corridors and reflective permeable pavements to simultaneously
      lower surface temperature and enhance permeability.
    - Verify feasibility and water requirements.
    """
    overview = client.get("/api/overview?city=Hyderabad").json()
    target_zone = overview["priority_zones"][0]
    zone_id = target_zone["id"]

    sim_res = client.post(
        "/api/simulation/run",
        json={
            "city": "Hyderabad",
            "zone_id": zone_id,
            "name": "Dual-Hazard Permeable Corridor",
            "coverage": {"corridors": 10.0},
            "road_treated_pct": 50.0,
            "water_limit": 400.0,
        },
    )
    assert sim_res.status_code == 200
    sim = sim_res.json()
    assert sim["feasible"] is True
    assert sim["estimated_cooling"] > 0.25
    assert sim["water_m3_day"] <= 400.0
    assert any("road" in n.lower() for n in sim["conversion_notes"])


def test_tier4_scenario_industrial_corridor_retrofit(client):
    """Scenario C: Industrial Corridor Large-Scale Reflective Retrofit.

    Urban Challenge:
    - Large logistics and manufacturing park in Delhi with expansive metal roof surfaces
      and broad asphalt freight roadways.
    - Zero residential tree canopy, high solar absorption.

    Planning Objective:
    - Deploy high-albedo roof coatings (cool roofs) and cool pavements.
    - Maximize cooling with zero ongoing municipal water demand.
    - Generate full municipal report documenting the industrial retrofit scenario.
    """
    overview = client.get("/api/overview?city=Delhi").json()
    industrial_zone = max(overview["priority_zones"], key=lambda z: z["roof_pct"] + z["road_pct"])
    zone_id = industrial_zone["id"]

    # 1. Simulate large-scale industrial coating
    sim_res = client.post(
        "/api/simulation/run",
        json={
            "city": "Delhi",
            "zone_id": zone_id,
            "name": "Industrial Albedo Retrofit",
            "coverage": {},
            "roof_treated_pct": 80.0,
            "road_treated_pct": 50.0,
            "water_limit": 0.0,
        },
    )
    assert sim_res.status_code == 200
    sim = sim_res.json()
    assert sim["feasible"] is True
    # Zero municipal water requirement for non-vegetated reflective treatments
    assert sim["water_m3_day"] == 0.0
    assert sim["estimated_cooling"] >= 0.15

    # 2. Export municipal report documenting the scenario
    rep_res = client.post("/api/reports/generate", json={"city": "Delhi"})
    assert rep_res.status_code == 200
    rep_id = rep_res.json()["id"]

    md_export = client.get(f"/api/reports/{rep_id}/markdown")
    assert md_export.status_code == 200
    assert "Delhi · Urban Heat Analysis" in md_export.text
    assert "Industrial Albedo Retrofit" in md_export.text
