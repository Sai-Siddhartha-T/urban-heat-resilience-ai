"""Focused tests for normal-mode evidence discovery and persistence."""

from fastapi.testclient import TestClient

from app.db import assets, init_db, records, save, save_asset
from app.main import app
from app.provenance import provenance


def _live_provenance(city, source="Mock evidence", category="weather"):
    return provenance(
        source=source,
        category=category,
        city=city,
        observation_time="2026-01-02T03:00:00Z",
        units={"temperature_2m": "°C"},
    )


def test_evidence_routes_expose_summaries_payload_detail_and_city_layers():
    init_db()
    payload = {"marker": "detail-only-payload"}
    identifier = save_asset(
        "weather",
        payload,
        _live_provenance("Ahmedabad"),
    )

    with TestClient(app) as client:
        listed = client.get("/api/data/assets?city=Ahmedabad")
        detail = client.get(f"/api/data/assets/{identifier}?city=Ahmedabad")
        layers = client.get("/api/data/layers?city=Ahmedabad")
        wrong_city = client.get(f"/api/data/assets/{identifier}?city=Delhi")

    assert listed.status_code == 200
    item = next(asset for asset in listed.json() if asset["id"] == identifier)
    assert item["city"] == "Ahmedabad"
    assert "payload" not in item
    assert detail.status_code == 200
    assert detail.json()["payload"] == payload
    assert layers.status_code == 200
    assert layers.json()["city"] == "Ahmedabad"
    assert layers.json()["layers"]
    assert wrong_city.status_code == 404


def test_normal_evidence_routes_exclude_demo_assets_and_demo_ingestion(monkeypatch):
    init_db()
    demo_metadata = _live_provenance("Delhi")
    demo_metadata["mode"] = "demo"
    demo_payload = {"synthetic": True, "marker": "demo"}
    demo_id = save_asset("weather", demo_payload, demo_metadata)

    prepared = {
        "data": {
            "features": [{"properties": {}}],
            "metadata": {"city": "Delhi", "synthetic": True},
        },
    }
    monkeypatch.setattr("app.routes.data.activate_demo", lambda *args: prepared)

    def unexpected_persistence(*args, **kwargs):
        raise AssertionError("Explicit demo ingestion must not persist live evidence.")

    monkeypatch.setattr("app.routes.data.persist_acquisition", unexpected_persistence)

    with TestClient(app) as client:
        response = client.get("/api/data/assets?city=Delhi")
        hidden_demo = client.get(f"/api/data/assets/{demo_id}?city=Delhi")
        demo_ingest = client.post(
            "/api/data/ingest", json={"city": "Delhi", "source": "demo"}
        )

    assert response.status_code == 200
    assert all(asset["mode"] == "live" for asset in response.json())
    assert demo_id not in {asset["id"] for asset in response.json()}
    assert hidden_demo.status_code == 404
    assert demo_ingest.status_code == 200
    assert demo_ingest.json() == {
        "source": "synthetic_demo",
        "mode": "demo",
        "zones": 1,
        "metadata": prepared["data"]["metadata"],
    }


def test_live_weather_ingestion_persists_one_atomic_asset_and_record(monkeypatch):
    init_db()
    marker = "atomic-weather-ingestion"

    async def mocked_weather(lat, lon, start=None, end=None):
        result = {
            "source": "Mock Open-Meteo forecast",
            "synthetic": False,
            "latitude": lat,
            "longitude": lon,
            "data": {
                "current": {"temperature_2m": 32.5, "time": "2026-01-02T03:00:00Z"},
                "current_units": {"temperature_2m": "°C"},
            },
            "marker": marker,
        }
        # Model the adapter's legacy persistence call; acquisition_scope must defer it.
        save("weather", result)
        return result

    monkeypatch.setattr("app.routes.data.sources.weather", mocked_weather)

    with TestClient(app) as client:
        response = client.post(
            "/api/data/ingest",
            json={"city": "Hyderabad", "source": "weather"},
        )

    assert response.status_code == 200
    acquired = response.json()
    assert acquired["analysis_ready"] is False
    matching_records = [
        item for item in records("weather", city="Hyderabad")
        if item.get("marker") == marker
    ]
    matching_assets = [
        item for item in assets(city="Hyderabad", category="weather", mode="live")
        if item["payload"].get("marker") == marker
    ]
    assert len(matching_records) == 1
    assert len(matching_assets) == 1
    assert matching_records[0]["asset_id"] == acquired["asset_id"]
    assert matching_assets[0]["id"] == acquired["asset_id"]
    assert matching_records[0]["provenance"] == matching_assets[0]["provenance"]


def test_catalog_ingestion_stays_unavailable_until_it_contains_mappable_evidence(monkeypatch):
    init_db()
    marker = "catalog-only-evidence"

    async def mocked_catalog(lat, lon, start, end):
        return {
            "source": "Mock Copernicus catalog",
            "items": [{"id": marker, "collection": "sentinel-2"}],
        }

    monkeypatch.setattr("app.routes.data.sources.copernicus_catalog", mocked_catalog)

    with TestClient(app) as client:
        response = client.post(
            "/api/data/ingest",
            json={
                "city": "Ahmedabad",
                "source": "copernicus",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
            },
        )

    assert response.status_code == 200
    acquired = response.json()
    assert acquired["analysis_ready"] is False
    assert acquired["provenance"]["analysis_ready"] is False
    from app.services.evidence import map_layers

    catalog_asset = next(
        asset for asset in assets(city="Ahmedabad", mode="live")
        if asset["payload"].get("items", [{}])[0].get("id") == marker
    )
    layers = map_layers("Ahmedabad", [catalog_asset])
    assert all(layer["status"] == "unavailable" for layer in layers)
    assert all(layer["geojson"] is None for layer in layers)
