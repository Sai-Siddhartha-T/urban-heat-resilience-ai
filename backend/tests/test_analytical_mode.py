"""Request-scoped normal and demo mode contracts for analytical API routes."""

import copy
import importlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import state as state_service


def _demo_dataset(city, boundary=None, rural_reference=33.0):
    properties = {
        "id": f"{city.lower()}_demo_1",
        "name": "Demonstration zone",
        "city": city,
        "lst": 40.0,
        "rural_reference": rural_reference,
        "predicted_suhii": 3.0,
        "predicted_lst": 40.0,
        "interval_low": 2.5,
        "interval_high": 3.5,
        "source": "synthetic_demo",
        "shap": {"building_density": 0.4},
        "shap_base": 2.6,
        "hotspot": True,
        "area_km2": 1.0,
        "risk_score": 0.8,
        "risk_level": "High",
        "population": 1000,
        "population_density": 1000,
        "available_land_pct": 30.0,
        "roof_pct": 30.0,
        "road_pct": 20.0,
        "protected": False,
    }
    return {
        "type": "FeatureCollection",
        "metadata": {
            "city": city,
            "synthetic": True,
            "mode": "demo",
            "analysis_ready": True,
            "limitations": [],
        },
        "features": [{"type": "Feature", "properties": properties}],
    }


@pytest.fixture
def analytical_client(monkeypatch):
    state_service.clear_state()
    monkeypatch.setenv("HEATWISE_DEMO_MODE", "1")
    monkeypatch.setattr(state_service, "records", lambda *args, **kwargs: [])
    monkeypatch.setattr(state_service, "save", lambda *args, **kwargs: "demo-record")
    monkeypatch.setattr(state_service, "sample_data", _demo_dataset)

    analysis_count = 0

    def fake_analyze(data, retrain=False):
        nonlocal analysis_count
        analysis_count += 1
        return {
            "data": copy.deepcopy(data),
            "model": {
                "winner": "test-model",
                "evaluations": [],
                "split": {"method": "test"},
                "training_number": analysis_count,
            },
            "importance": [{"feature": "building_density", "importance": 0.4}],
            "artifact": None,
        }

    monkeypatch.setattr(state_service, "analyze", fake_analyze)

    for module_name in (
        "app.routes.ai",
        "app.routes.risk",
        "app.routes.simulation",
        "app.routes.optimization",
        "app.routes.reports",
    ):
        module = importlib.import_module(module_name)
        if hasattr(module, "save"):
            monkeypatch.setattr(module, "save", lambda *args, **kwargs: "saved")
    ai_route = importlib.import_module("app.routes.ai")
    monkeypatch.setattr(ai_route, "records", lambda *args, **kwargs: [])

    async def fake_chat(*args, **kwargs):
        return {
            "summary": "Demo response",
            "findings": [],
            "actions": [],
            "limitations": [],
            "provider": "local",
            "fallback": True,
            "facts": {},
        }

    monkeypatch.setattr(ai_route.ai, "chat", fake_chat)

    optimization_route = importlib.import_module("app.routes.optimization")
    monkeypatch.setattr(
        optimization_route,
        "optimize",
        lambda *args, **kwargs: {
            "status": "No feasible plan",
            "feasible": False,
            "selections": [],
            "violations": [],
            "hypothetical": True,
            "assumptions": [],
        },
    )

    with TestClient(app) as client:
        yield client
    state_service.clear_state()


def test_analytical_routes_require_request_scoped_demo_mode(analytical_client):
    client = analytical_client

    # Explicit normal analytical requests cannot use synthetic data without verified evidence.
    assert client.get("/api/overview?city=Ahmedabad&mode=normal").status_code == 409
    assert (
        client.post("/api/heat/predict", json={"city": "Ahmedabad", "mode": "normal"}).status_code
        == 409
    )
    assert "Ahmedabad" not in state_service.DEMO_STATE
    assert "Ahmedabad" not in state_service.REAL_STATE

    activation = client.post(
        "/api/data/ingest",
        json={"city": "Ahmedabad", "source": "demo"},
    )
    assert activation.status_code == 200
    assert activation.json()["mode"] == "demo"

    # Representative GET and POST heat routes receive explicit demo mode.
    assert client.get("/api/overview?city=Ahmedabad&mode=demo").status_code == 200
    assert client.get("/api/heat/map?mode=demo").json()["metadata"]["synthetic"] is True
    assert client.get("/api/heat/hotspots?mode=demo").status_code == 200
    assert client.get("/api/heat/predict?mode=demo").status_code == 200
    prediction = client.post("/api/heat/predict", json={"mode": "demo"})
    assert prediction.status_code == 200
    assert prediction.json()["predictions"][0]["source"] == "synthetic_demo"

    # GET and POST analytical endpoints consistently select the demo cache.
    assert client.get("/api/models?mode=demo").status_code == 200
    assert client.get("/api/xai/importance?mode=demo").status_code == 200
    assert client.get("/api/xai/shap?mode=demo").status_code == 200
    assert client.post("/api/xai/explain", json={"mode": "demo"}).status_code == 200
    assert client.post("/api/xai/shap", json={"mode": "demo"}).status_code == 200
    assert client.post("/api/risk/analyze", json={"mode": "demo"}).status_code == 200
    assert (
        client.post(
            "/api/simulation/run",
            json={"mode": "demo", "coverage": {"cool_roofs": 5}},
        ).status_code
        == 200
    )
    assert (
        client.post("/api/optimization/run", json={"mode": "demo"}).status_code
        == 200
    )
    assert (
        client.post(
            "/api/ai/chat",
            json={"mode": "demo", "message": "Explain this demonstration zone."},
        ).status_code
        == 200
    )
    assert client.post("/api/reports/generate", json={"mode": "demo"}).status_code == 200


def test_retraining_updates_the_cache_selected_by_request_mode(analytical_client):
    demo_cache_before = state_service.state("Ahmedabad", "demo")
    response = analytical_client.post(
        "/api/models/train",
        json={"city": "Ahmedabad", "mode": "demo"},
    )

    assert response.status_code == 200
    demo_cache_after = state_service.DEMO_STATE["Ahmedabad"]
    assert demo_cache_after is not demo_cache_before
    assert (
        demo_cache_after["model"]["training_number"]
        > demo_cache_before["model"]["training_number"]
    )
    assert "Ahmedabad" not in state_service.REAL_STATE
