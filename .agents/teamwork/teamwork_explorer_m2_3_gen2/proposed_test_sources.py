import asyncio
import os
import sys
from unittest.mock import MagicMock
import httpx
import numpy as np
import pytest

from app.db import init_db
from app.services import sources


# ---------------------------------------------------------------------------
# Test Isolation Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolate_test_state():
    """Ensure in-memory cache and database are isolated across all test cases."""
    sources._CACHE.clear()
    init_db()
    yield
    sources._CACHE.clear()


# ---------------------------------------------------------------------------
# 1. Preserved Existing Tests (5 tests)
# ---------------------------------------------------------------------------

def test_catalog_filters_clouds_and_preserves_dates(monkeypatch):
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


def test_power_rows_keep_missing_fill_values():
    rows = sources.power_rows(
        {
            "header": {"fill_value": -999},
            "properties": {
                "parameter": {
                    "T2M": {"20250501": 34.2, "20250502": -999},
                    "RH2M": {"20250501": 40, "20250502": 41},
                }
            },
        }
    )
    assert rows[0]["T2M"] == 34.2
    assert rows[1]["T2M"] is None
    assert rows[1]["date"] == "2025-05-02"


def test_weather_series_uses_only_retrieved_hours():
    series = sources.weather_series(
        [
            {
                "id": "w1",
                "source": "Open-Meteo forecast",
                "latitude": 23.0,
                "longitude": 72.5,
                "data": {
                    "hourly": {
                        "time": ["2025-05-01T00:00", "2025-05-01T01:00", "2025-05-02T00:00"],
                        "temperature_2m": [30, None, 32],
                        "relative_humidity_2m": [50, 55, None],
                    }
                },
            }
        ]
    )
    points = series["series"][0]["points"]
    assert points[0]["date"] == "2025-05-01"
    assert points[0]["hours_with_temperature"] == 1
    assert points[0]["air_temperature_c"] == 30
    assert points[1]["air_temperature_c"] == 32
    assert points[1]["relative_humidity_pct"] is None
    assert "not SUHII" in series["note"]


def test_copernicus_keeps_catalog_metadata_only(monkeypatch):
    async def fake(url, body, headers=None):
        assert "stac.dataspace.copernicus.eu" in url
        assert body["collections"] == ["sentinel-2-l2a"]
        return {
            "features": [
                {
                    "id": "S2",
                    "bbox": [72, 23, 73, 24],
                    "properties": {
                        "datetime": "2025-05-02T05:00:00Z",
                        "eo:cloud_cover": 4,
                    },
                    "assets": {"B04": {"href": "https://example.invalid/B04.jp2"}},
                }
            ]
        }

    monkeypatch.setattr(sources, "post_json", fake)
    result = asyncio.run(sources.copernicus_catalog(23.02, 72.57, "2025-05-01", "2025-05-03"))
    assert result["scene_count"] == 1
    assert "assets" not in result["scenes"][0]
    assert result["synthetic"] is False


def test_osm_geometry_conversion(monkeypatch):
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


# ---------------------------------------------------------------------------
# 2. Open-Meteo Weather Unit Tests (3 tests)
# ---------------------------------------------------------------------------

def test_weather_era5_reanalysis(monkeypatch):
    captured_calls = []

    async def fake_get(url, params=None, headers=None):
        captured_calls.append({"url": url, "params": params})
        return {
            "hourly": {
                "time": ["2025-05-01T00:00", "2025-05-01T01:00"],
                "temperature_2m": [32.5, 33.1],
                "soil_moisture_0_to_7cm": [0.15, 0.14],
            }
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.weather(23.02, 72.57, start="2025-05-01", end="2025-05-02"))

    assert len(captured_calls) == 1
    assert "archive-api.open-meteo.com" in captured_calls[0]["url"]
    params = captured_calls[0]["params"]
    assert params["latitude"] == 23.02
    assert params["longitude"] == 72.57
    assert params["start_date"] == "2025-05-01"
    assert params["end_date"] == "2025-05-02"
    assert params["models"] == "era5_land"
    assert "soil_moisture_0_to_7cm" in params["hourly"]

    assert result["source"] == "Open-Meteo ERA5-Land"
    assert result["synthetic"] is False
    assert result["latitude"] == 23.02
    assert result["longitude"] == 72.57
    assert "data" in result


def test_weather_forecast_mode(monkeypatch):
    captured_calls = []

    async def fake_get(url, params=None, headers=None):
        captured_calls.append({"url": url, "params": params})
        return {
            "current": {"temperature_2m": 35.0, "relative_humidity_2m": 45},
            "hourly": {
                "time": ["2025-05-01T00:00"],
                "temperature_2m": [35.0],
                "soil_moisture_0_to_1cm": [0.08],
            },
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.weather(23.02, 72.57))

    assert len(captured_calls) == 1
    assert "api.open-meteo.com/v1/forecast" in captured_calls[0]["url"]
    params = captured_calls[0]["params"]
    assert params["forecast_days"] == 3
    assert "current" in params
    assert "soil_moisture_0_to_1cm" in params["hourly"]

    assert result["source"] == "Open-Meteo forecast"
    assert result["synthetic"] is False


def test_weather_upstream_error(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        raise httpx.ConnectError("Open-Meteo upstream gateway unreachable")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.weather(23.02, 72.57))


# ---------------------------------------------------------------------------
# 3. OpenAQ v3 Air Quality Unit Tests (4 tests)
# ---------------------------------------------------------------------------

def test_air_quality_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAQ_API_KEY is not configured"):
        asyncio.run(sources.air_quality(23.02, 72.57))


def test_air_quality_success(monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "test-secret-key")
    captured_headers = []

    async def fake_get(url, params=None, headers=None):
        captured_headers.append(headers)
        if "locations/" in url and "/latest" in url:
            loc_id = url.split("locations/")[1].split("/latest")[0]
            return {"results": [{"parameter": "pm25", "value": 45.2, "locationId": int(loc_id)}]}
        return {
            "results": [
                {"id": 101, "name": "Station Alpha"},
                {"id": 102, "name": "Station Beta"},
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.air_quality(23.02, 72.57))

    assert result["source"] == "OpenAQ v3"
    assert result["synthetic"] is False
    assert len(result["latest"]) == 2
    assert result["latest_unavailable_location_ids"] == []
    assert all(h.get("X-API-Key") == "test-secret-key" for h in captured_headers if h)


def test_air_quality_station_fault_tolerance(monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "test-secret-key")

    async def fake_get(url, params=None, headers=None):
        if "locations/" in url and "/latest" in url:
            loc_id = int(url.split("locations/")[1].split("/latest")[0])
            if loc_id == 102:
                # Simulate station 102 failing upstream
                raise httpx.HTTPStatusError("Station sensor decommissioned", request=None, response=None)
            return {"results": [{"parameter": "pm25", "value": 28.4, "locationId": loc_id}]}
        return {
            "results": [
                {"id": 101, "name": "Station 1"},
                {"id": 102, "name": "Station 2 (Failing)"},
                {"id": 103, "name": "Station 3"},
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.air_quality(23.02, 72.57))

    # Must NOT fail the entire batch when station 102 fails
    assert len(result["latest"]) == 2
    assert [item["location_id"] for item in result["latest"]] == [101, 103]
    assert result["latest_unavailable_location_ids"] == [102]


def test_air_quality_discovery_error(monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "test-secret-key")

    async def fake_get(url, params=None, headers=None):
        raise httpx.ConnectTimeout("OpenAQ location discovery timed out")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.air_quality(23.02, 72.57))


# ---------------------------------------------------------------------------
# 4. WorldPop STAC Unit Tests (3 tests)
# ---------------------------------------------------------------------------

def test_worldpop_success_and_year_filter(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        assert params == {"iso3": "IND"}
        return {
            "data": [
                {"id": "w1", "popyear": 2020, "desc": "India 2020 population"},
                {"id": "w2", "year": "2020", "desc": "India 2020 alt field"},
                {"id": "w3", "popyear": 2015, "desc": "India 2015 historical"},
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.worldpop(country="IND", year=2020))

    assert result["source"] == "WorldPop catalog"
    assert result["synthetic"] is False
    assert result["country"] == "IND"
    assert result["year"] == 2020
    assert len(result["datasets"]) == 2
    assert [d["id"] for d in result["datasets"]] == ["w1", "w2"]


def test_worldpop_empty_when_no_match(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        return {"data": [{"id": "w1", "popyear": 2010}]}

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.worldpop(country="IND", year=2020))
    assert result["datasets"] == []


def test_worldpop_upstream_error(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        raise httpx.HTTPError("WorldPop catalog service unavailable")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.worldpop(country="IND", year=2020))


# ---------------------------------------------------------------------------
# 5. GHSL STAC Unit Tests (4 tests)
# ---------------------------------------------------------------------------

def test_ghsl_catalog_success(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        assert params["bbox"] == "72.45,22.95,72.55,23.05"
        return {
            "features": [
                {
                    "id": "ghsl_tile_1",
                    "collection": "jrc_ghsl_pop",
                    "bbox": [72.45, 22.95, 72.55, 23.05],
                    "properties": {"datetime": "2020-01-01T00:00:00Z"},
                    "assets": {"data": {"href": "https://example.com/ghsl_tile_1.tif"}},
                }
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.ghsl_catalog(23.0, 72.5))

    assert result["source"] == "GHSL GHS-POP via Humanitarian Data Cube STAC"
    assert result["synthetic"] is False
    assert len(result["tiles"]) == 1
    assert result["tiles"][0]["id"] == "ghsl_tile_1"
    assert result["tiles"][0]["asset_href"] == "https://example.com/ghsl_tile_1.tif"


def test_ghsl_catalog_fallback_asset(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        return {
            "features": [
                {
                    "id": "ghsl_tile_fallback",
                    "collection": "jrc_ghsl_pop",
                    "properties": {"start_datetime": "2020-01-01T00:00:00Z"},
                    "assets": {"default_raster": {"href": "https://example.com/fallback.tif"}},
                }
            ]
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.ghsl_catalog(23.0, 72.5))
    assert result["tiles"][0]["asset_href"] == "https://example.com/fallback.tif"


def test_ghsl_catalog_empty_tiles_raises_value_error(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        return {"features": []}

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(ValueError, match="No GHSL population tiles intersect"):
        asyncio.run(sources.ghsl_catalog(23.0, 72.5))


def test_ghsl_catalog_upstream_error(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        raise httpx.HTTPError("Humanitarian Data Cube STAC offline")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.ghsl_catalog(23.0, 72.5))


# ---------------------------------------------------------------------------
# 6. Sentinel-2 COG WarpedVRT Unit Tests (4 tests)
# ---------------------------------------------------------------------------

def test_sentinel_indices_empty_catalog_raises_value_error():
    with pytest.raises(ValueError, match="No scenes pass the cloud filter"):
        sources.sentinel_indices({"features": []}, 23.0, 72.5)


def test_sentinel_indices_ssrf_protection():
    catalog = {
        "features": [
            {
                "id": "malicious_scene",
                "properties": {"datetime": "2025-05-01T00:00:00Z"},
                "assets": {
                    "red": {"href": "https://attacker.com/exploit.tif"},
                    "nir": {"href": "https://attacker.com/exploit.tif"},
                    "green": {"href": "https://attacker.com/exploit.tif"},
                    "swir16": {"href": "https://attacker.com/exploit.tif"},
                    "scl": {"href": "https://attacker.com/exploit.tif"},
                },
            }
        ]
    }
    with pytest.raises(ValueError, match="Unexpected satellite asset host."):
        sources.sentinel_indices(catalog, 23.0, 72.5)


def test_sentinel_indices_calculation(monkeypatch):
    import rasterio
    from rasterio.vrt import WarpedVRT

    # Synthetic 32x32 band arrays:
    # NIR = 4000 (reflectance = 0.4), Red = 2000 (reflectance = 0.2)
    # NDVI = (0.4 - 0.2) / (0.4 + 0.2) = 0.2 / 0.6 = 0.333333
    band_data = {
        "red": np.full((32, 32), 2000.0),
        "nir": np.full((32, 32), 4000.0),
        "green": np.full((32, 32), 1500.0),
        "swir16": np.full((32, 32), 1000.0),
        "scl": np.full((32, 32), 4.0),  # Valid vegetation class
    }

    class MockSrc:
        def __init__(self, href):
            self.href = href
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class MockVRT:
        def __init__(self, src, **kwargs):
            self.src = src
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, idx):
            for k in ["red", "nir", "green", "swir16", "scl"]:
                if f"_{k}.tif" in self.src.href:
                    return band_data[k]
            return np.zeros((32, 32))

    monkeypatch.setattr(rasterio, "open", lambda href: MockSrc(href))
    import rasterio.vrt
    monkeypatch.setattr(rasterio.vrt, "WarpedVRT", MockVRT)

    base = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/test"
    catalog = {
        "features": [
            {
                "id": "s2_test_scene",
                "properties": {"datetime": "2025-05-02T10:00:00Z"},
                "assets": {
                    "red": {"href": f"{base}_red.tif", "raster:bands": [{"scale": 0.0001, "offset": 0}]},
                    "nir": {"href": f"{base}_nir.tif", "raster:bands": [{"scale": 0.0001, "offset": 0}]},
                    "green": {"href": f"{base}_green.tif", "raster:bands": [{"scale": 0.0001, "offset": 0}]},
                    "swir16": {"href": f"{base}_swir16.tif", "raster:bands": [{"scale": 0.0001, "offset": 0}]},
                    "scl": {"href": f"{base}_scl.tif"},
                },
            }
        ]
    }

    result = sources.sentinel_indices(catalog, 23.0, 72.5)

    assert result["source"] == "Sentinel-2 L2A COG / Earth Search"
    assert result["synthetic"] is False
    assert result["valid_pixels"] == 1024  # 32 * 32
    assert result["shape"] == [32, 32]
    assert result["resolution_m"] == 100
    assert pytest.approx(result["indices"]["ndvi"]["mean"], rel=1e-3) == 0.333333


def test_sentinel_indices_all_cloud_edge_case(monkeypatch):
    import rasterio

    # When all pixels are cloud (SCL=9), valid_pixels must be 0 and mean must be None
    band_data = {
        "red": np.full((32, 32), 2000.0),
        "nir": np.full((32, 32), 4000.0),
        "green": np.full((32, 32), 1500.0),
        "swir16": np.full((32, 32), 1000.0),
        "scl": np.full((32, 32), 9.0),  # High probability cloud
    }

    class MockSrc:
        def __init__(self, href):
            self.href = href
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class MockVRT:
        def __init__(self, src, **kwargs):
            self.src = src
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, idx):
            for k in ["red", "nir", "green", "swir16", "scl"]:
                if f"_{k}.tif" in self.src.href:
                    return band_data[k]
            return np.zeros((32, 32))

    monkeypatch.setattr(rasterio, "open", lambda href: MockSrc(href))
    import rasterio.vrt
    monkeypatch.setattr(rasterio.vrt, "WarpedVRT", MockVRT)

    base = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/test"
    catalog = {
        "features": [
            {
                "id": "s2_cloud_scene",
                "properties": {"datetime": "2025-05-02T10:00:00Z"},
                "assets": {
                    "red": {"href": f"{base}_red.tif"},
                    "nir": {"href": f"{base}_nir.tif"},
                    "green": {"href": f"{base}_green.tif"},
                    "swir16": {"href": f"{base}_swir16.tif"},
                    "scl": {"href": f"{base}_scl.tif"},
                },
            }
        ]
    }

    result = sources.sentinel_indices(catalog, 23.0, 72.5)
    assert result["valid_pixels"] == 0
    assert result["indices"]["ndvi"]["mean"] is None
    assert result["indices"]["ndwi"]["mean"] is None
    assert result["indices"]["ndbi"]["mean"] is None


# ---------------------------------------------------------------------------
# 7. Google Earth Engine Unit Tests (5 tests)
# ---------------------------------------------------------------------------

def test_earth_engine_missing_project_raises_value_error(monkeypatch):
    monkeypatch.delenv("EARTH_ENGINE_PROJECT", raising=False)
    boundary = [[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.0]]
    with pytest.raises(ValueError, match="EARTH_ENGINE_PROJECT and Google application credentials are required."):
        sources.earth_engine(boundary, "2025-05-01", "2025-05-31")


def test_earth_engine_empty_scenes_raises_value_error(monkeypatch):
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "mock-project-id")
    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_col.merge.return_value = mock_col
    mock_col.filterBounds.return_value = mock_col
    mock_col.filterDate.return_value = mock_col
    mock_col.filter.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 0

    monkeypatch.setitem(sys.modules, "ee", mock_ee)
    boundary = [[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.0]]
    with pytest.raises(ValueError, match="No Landsat scenes available"):
        sources.earth_engine(boundary, "2025-05-01", "2025-05-31")


def test_earth_engine_success(monkeypatch):
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "mock-project-id")
    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_img = MagicMock()

    mock_ee.ImageCollection.return_value = mock_col
    mock_col.merge.return_value = mock_col
    mock_col.filterBounds.return_value = mock_col
    mock_col.filterDate.return_value = mock_col
    mock_col.filter.return_value = mock_col
    mock_col.map.return_value = mock_col
    mock_col.median.return_value = mock_img

    mock_col.size.return_value.getInfo.return_value = 4
    mock_col.aggregate_array.return_value.getInfo.return_value = [1714521600000, 1714608000000]

    sample_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.55, 23.05]},
                "properties": {"ndvi": 0.42, "lst": 38.5, "ndwi": -0.15, "ndbi": 0.12},
            }
        ],
    }
    mock_img.sample.return_value.getInfo.return_value = sample_fc

    for method in [
        "select", "rename", "multiply", "add", "subtract", "bitwiseAnd",
        "rightShift", "eq", "gte", "lte", "And", "addBands", "updateMask",
        "copyProperties", "normalizedDifference"
    ]:
        setattr(mock_img, method, MagicMock(return_value=mock_img))

    monkeypatch.setitem(sys.modules, "ee", mock_ee)
    boundary = [[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.0]]

    result = sources.earth_engine(boundary, "2025-05-01", "2025-05-31")

    assert result["source"] == "Landsat 8/9 Collection 2 L2"
    assert result["synthetic"] is False
    assert result["scene_count"] == 4
    assert result["acquisition_dates_ms"] == [1714521600000, 1714608000000]
    assert result["crs"] == "EPSG:6933"
    assert result["samples"]["features"][0]["properties"]["ndvi"] == 0.42
    assert result["ndbai"] is None


def test_supplementary_earth_engine_products(monkeypatch):
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "mock-project-id")
    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_img = MagicMock()

    mock_ee.ImageCollection.return_value = mock_col
    mock_ee.Image.return_value = mock_img
    mock_col.filterBounds.return_value = mock_col
    mock_col.filterDate.return_value = mock_col
    mock_col.filter.return_value = mock_col
    mock_col.map.return_value = mock_col
    mock_col.median.return_value = mock_img
    mock_col.mean.return_value = mock_img
    mock_col.first.return_value = mock_img

    mock_col.size.return_value.getInfo.return_value = 2
    mock_col.aggregate_array.return_value.getInfo.return_value = [1714521600000]

    sample_fc = {"type": "FeatureCollection", "features": []}
    mock_img.sample.return_value.getInfo.return_value = sample_fc

    for method in [
        "select", "rename", "multiply", "add", "subtract", "bitwiseAnd",
        "rightShift", "eq", "gte", "lte", "And", "addBands", "updateMask",
        "copyProperties", "normalizedDifference"
    ]:
        setattr(mock_img, method, MagicMock(return_value=mock_img))

    monkeypatch.setitem(sys.modules, "ee", mock_ee)
    boundary = [[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.0]]

    # 1. Sentinel
    r_sent = sources.supplementary_earth_engine("sentinel", boundary, "2025-05-01", "2025-05-31")
    assert r_sent["native_resolution"] == "10 m visible/NIR; 20 m SWIR/SCL"
    assert r_sent["synthetic"] is False

    # 2. MODIS
    r_modis = sources.supplementary_earth_engine("modis", boundary, "2025-05-01", "2025-05-31")
    assert r_modis["native_resolution"] == "1 km / 8-day composites"

    # 3. ESA WorldCover
    r_wc = sources.supplementary_earth_engine("worldcover", boundary, "2025-05-01", "2025-05-31")
    assert r_wc["native_resolution"] == "10 m"

    # 4. SRTM
    r_srtm = sources.supplementary_earth_engine("srtm", boundary, "2025-05-01", "2025-05-31")
    assert r_srtm["native_resolution"] == "30 m"

    # 5. Unknown product
    with pytest.raises(ValueError, match="Unknown satellite product."):
        sources.supplementary_earth_engine("unknown_hyperspectral", boundary, "2025-05-01", "2025-05-31")


def test_supplementary_earth_engine_empty_collection(monkeypatch):
    monkeypatch.setenv("EARTH_ENGINE_PROJECT", "mock-project-id")
    mock_ee = MagicMock()
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_col.filterBounds.return_value = mock_col
    mock_col.filterDate.return_value = mock_col
    mock_col.filter.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 0

    monkeypatch.setitem(sys.modules, "ee", mock_ee)
    boundary = [[72.5, 23.0], [72.6, 23.0], [72.6, 23.1], [72.5, 23.0]]

    with pytest.raises(ValueError, match="No Sentinel-2 scenes pass cloud and date filters."):
        sources.supplementary_earth_engine("sentinel", boundary, "2025-05-01", "2025-05-31")

    with pytest.raises(ValueError, match="No MODIS composites in the date range."):
        sources.supplementary_earth_engine("modis", boundary, "2025-05-01", "2025-05-31")


# ---------------------------------------------------------------------------
# 8. OSM Overpass Mirror Failover & Resilience Unit Tests (2 tests)
# ---------------------------------------------------------------------------

def test_osm_mirror_failover_primary_fails_secondary_succeeds(monkeypatch):
    calls = []

    async def fake_get(url, params=None, headers=None):
        calls.append(url)
        if url == sources.OVERPASS_URLS[0]:
            # Primary mirror fails
            raise httpx.HTTPStatusError("504 Gateway Timeout", request=None, response=None)
        # Secondary mirror succeeds
        return {
            "elements": [
                {
                    "id": 999,
                    "tags": {"highway": "primary"},
                    "geometry": [{"lon": 72.5, "lat": 23.0}, {"lon": 72.6, "lat": 23.1}],
                }
            ],
            "osm3s": {"timestamp_osm_base": "2025-05-01T00:00:00Z"},
        }

    monkeypatch.setattr(sources, "get_json", fake_get)
    result = asyncio.run(sources.osm(23.0, 72.5))

    # Verify both mirrors were attempted in order
    assert calls == sources.OVERPASS_URLS
    assert len(result["metadata"]["endpoint_failures"]) == 1
    assert result["metadata"]["endpoint_failures"][0]["endpoint"] == sources.OVERPASS_URLS[0]
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["osm_id"] == 999


def test_osm_mirror_failover_both_fail_raises_httperror(monkeypatch):
    calls = []

    async def fake_get(url, params=None, headers=None):
        calls.append(url)
        raise httpx.ConnectError(f"Connection refused on {url}")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError, match="OpenStreetMap Overpass mirrors were unavailable"):
        asyncio.run(sources.osm(23.0, 72.5))

    assert calls == sources.OVERPASS_URLS


# ---------------------------------------------------------------------------
# 9. NASA POWER & Copernicus STAC Edge Cases (3 tests)
# ---------------------------------------------------------------------------

def test_power_rows_invalid_responses():
    with pytest.raises(ValueError, match="NASA POWER response did not include a parameter table."):
        sources.power_rows({"properties": {}})

    with pytest.raises(ValueError, match="NASA POWER returned no parameters."):
        sources.power_rows({"properties": {"parameter": {}}})

    with pytest.raises(ValueError, match="NASA POWER returned no daily rows"):
        sources.power_rows({"properties": {"parameter": {"T2M": {}}}})


def test_nasa_power_network_failure(monkeypatch):
    async def fake_get(url, params=None, headers=None):
        raise httpx.ConnectError("NASA POWER server unavailable")

    monkeypatch.setattr(sources, "get_json", fake_get)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.nasa_power(23.0, 72.5, "2025-05-01", "2025-05-02"))


def test_copernicus_catalog_network_failure(monkeypatch):
    async def fake_post(url, body, headers=None):
        raise httpx.HTTPError("Copernicus STAC timed out")

    monkeypatch.setattr(sources, "post_json", fake_post)
    with pytest.raises(httpx.HTTPError):
        asyncio.run(sources.copernicus_catalog(23.0, 72.5, "2025-05-01", "2025-05-02"))


# ---------------------------------------------------------------------------
# 10. Cache Determinism & Isolation Verification (1 test)
# ---------------------------------------------------------------------------

def test_cache_hit_and_isolation(monkeypatch):
    counter = 0

    async def fake_get(url, params=None, headers=None):
        nonlocal counter
        counter += 1
        return {"data": f"call_{counter}"}

    # Use actual sources.get_json with mocked httpx.AsyncClient
    sources._CACHE.clear()

    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            nonlocal counter
            counter += 1
            return {"count": counter}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, params=None, headers=None):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    # First call: cache miss, triggers get
    r1 = asyncio.run(sources.get_json("https://example.com/test", {"q": 1}))
    assert r1 == {"count": 1}
    assert counter == 1

    # Second call with same url & params: cache hit! counter does not increment
    r2 = asyncio.run(sources.get_json("https://example.com/test", {"q": 1}))
    assert r2 == {"count": 1}
    assert counter == 1

    # Clear cache -> next call must be cache miss!
    sources._CACHE.clear()
    r3 = asyncio.run(sources.get_json("https://example.com/test", {"q": 1}))
    assert r3 == {"count": 2}
    assert counter == 2
