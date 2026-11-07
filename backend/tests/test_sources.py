import asyncio
import httpx
from app.db import init_db
from app.services import sources


def test_catalog_filters_clouds_and_preserves_dates(monkeypatch):
    init_db()

    async def fake(*args, **kwargs):
        return {
            "features": [
                {
                    "id": "clear",
                    "properties": {
                        "eo:cloud_cover": 5,
                        "datetime": "2025-05-03T00:00:00Z",
                    },
                },
                {
                    "id": "cloudy",
                    "properties": {
                        "eo:cloud_cover": 80,
                        "datetime": "2025-05-04T00:00:00Z",
                    },
                },
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake)
    r = asyncio.run(sources.sentinel_catalog(23, 72, "2025-05-01", "2025-05-31"))
    assert [f["id"] for f in r["features"]] == ["clear"]
    assert not r["metadata"]["synthetic"] and r["metadata"]["acquisition_dates"] == [
        "2025-05-03T00:00:00Z"
    ]


def test_osm_geometry_conversion(monkeypatch):
    init_db()

    async def fake(*args, **kwargs):
        return {
            "elements": [
                {
                    "id": 1,
                    "tags": {"building": "yes"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 0},
                    ],
                }
            ],
            "osm3s": {"timestamp_osm_base": "2025-01-01"},
        }

    monkeypatch.setattr(sources, "get_json", fake)
    result = asyncio.run(sources.osm(23, 72))
    assert result["features"][0]["geometry"]["type"] == "Polygon"
    assert result["metadata"]["osm_timestamp"] == "2025-01-01"
