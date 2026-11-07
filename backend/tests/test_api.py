import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_integrated_workflow(client):
    overview = client.get("/api/overview").json()
    zone_id = overview["priority_zones"][0]["id"]
    prediction = client.post("/api/heat/predict", json={"zone_id": zone_id}).json()
    assert prediction["predicted_suhii"] > 0
    explanation = client.post("/api/xai/explain", json={"zone_id": zone_id}).json()
    assert (
        abs(
            explanation["base_value"]
            + sum(explanation["contributions"].values())
            - prediction["predicted_suhii"]
        )
        < 1e-4
    )
    risk = client.post(
        "/api/risk/analyze", json={"zone_id": zone_id, "hazard_weight": 1.5}
    )
    assert risk.status_code == 200
    simulation = client.post(
        "/api/simulation/run",
        json={
            "zone_id": zone_id,
            "coverage": {"cool_roofs": 5},
            "name": "API verification",
        },
    )
    assert simulation.status_code == 200 and simulation.json()["feasible"]
    optimization = client.post("/api/optimization/run", json={"water_limit": 400})
    assert optimization.status_code == 200 and optimization.json()["water_used"] <= 400
    chat = client.post(
        "/api/ai/chat",
        json={
            "message": "Why is this zone hot?",
            "provider": "local",
            "zone_id": zone_id,
        },
    )
    assert chat.status_code == 200 and chat.json()["fallback"]
    assert (
        chat.json()["facts"]["prediction"]["suhii_c"] == prediction["predicted_suhii"]
    )
    report = client.post("/api/reports/generate", json={}).json()
    for key in ["download_url", "csv_url", "markdown_url"]:
        r = client.get(report[key])
        assert r.status_code == 200 and len(r.content) > 100
    assert "SYNTHETIC DEMONSTRATION" in client.get(report["markdown_url"]).text


def test_input_errors(client):
    assert (
        client.post(
            "/api/data/ingest", json={"latitude": 100, "longitude": 1}
        ).status_code
        == 422
    )
    assert client.post("/api/data/ingest", json={"latitude": 20}).status_code == 422
    assert (
        client.post(
            "/api/data/ingest",
            json={"start_date": "2025-06-01", "end_date": "2025-05-01"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/data/ingest",
            json={"boundary": {"type": "Point", "coordinates": [0, 0]}},
        ).status_code
        == 422
    )
    assert (
        client.post("/api/simulation/run", json={"coverage": {"trees": -1}}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/simulation/run", json={"coverage": {"unknown": 5}}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/heat/predict", json={"zone_id": "missing"}).status_code == 404
    )
    assert client.get("/api/heat/map?city=missing").status_code == 422
    assert client.get("/api/reports/missing/download").status_code == 404
    assert (
        client.post(
            "/api/optimization/run", json={"zone_ids": ["same", "same"]}
        ).status_code
        == 422
    )


def test_unconfigured_provider_fallback(client, monkeypatch):
    for key in ["GROQ_API_KEY", "GEMINI_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    r = client.post(
        "/api/ai/chat", json={"message": "Explain the evidence", "provider": "auto"}
    )
    assert (
        r.status_code == 200 and r.json()["fallback"] and len(r.json()["failures"]) == 2
    )


def test_api_token(client, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-token")
    assert client.get("/api/health").status_code == 401
    assert (
        client.get(
            "/api/health", headers={"Authorization": "Bearer test-token"}
        ).status_code
        == 200
    )


def test_upstream_failure_is_explicit(client, monkeypatch):
    import httpx
    from app.services import sources

    async def fail(*args, **kwargs):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(sources, "weather", fail)
    r = client.post("/api/data/ingest", json={"source": "weather"})
    assert r.status_code == 502 and "No substitute data" in r.json()["detail"]
