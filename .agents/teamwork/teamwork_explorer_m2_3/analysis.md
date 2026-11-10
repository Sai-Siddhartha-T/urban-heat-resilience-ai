# Comprehensive Analysis & Test Blueprint: Data Source Adapters & Test Resilience

**Date**: 2026-11-08  
**Author**: Explorer M2-3 — Adapter Unit Test Expansion & Test Resilience Specialist  
**Workspace**: `d:\Urban-Heat-Resilience-AI`  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3`  
**Target Modules**: `backend/app/services/sources.py`, `backend/tests/test_sources.py`, `backend/app/main.py`

---

## 1. Executive Summary & Objective

The **AI-Powered Urban Heat Resilience & Mitigation Platform** integrates meteorological and geospatial observations from 11 distinct external providers. As documented in the project architectural constitution:
> **Strict Data Provenance Principle**: Real-world satellite, meteorological, and infrastructure observations must remain strictly decoupled from the synthetic demonstration model. When external upstream providers fail, experience network timeouts, or return invalid responses, the system **must fail explicitly with HTTP 502 Bad Gateway** and never masquerade synthetic or imputed data as live observations.

### Current Deficit (Identified in Survey 3):
- `backend/app/services/sources.py` contains 769 lines of production adapter logic.
- Only **4 adapters** had partial unit test coverage in `backend/tests/test_sources.py` (5 tests total).
- **6 adapters lacked unit tests entirely**:
  1. **Open-Meteo Weather** (`sources.weather()`)
  2. **OpenAQ v3 Air Quality** (`sources.air_quality()`)
  3. **WorldPop Catalog** (`sources.worldpop()`)
  4. **GHSL Population Catalog** (`sources.ghsl_catalog()`)
  5. **Sentinel-2 Cloud-Optimized GeoTIFF Reader** (`sources.sentinel_indices()`)
  6. **Google Earth Engine** (`sources.earth_engine()` and `sources.supplementary_earth_engine()`)
- Critical resilience mechanisms—notably the **OpenStreetMap dual-mirror failover loop** and **per-station fault isolation in OpenAQ**—had no automated test validation.
- In-memory cache (`sources._CACHE`) lacked test isolation, causing potential cache bleed across test cases.

### Deliverable:
This document provides a comprehensive architectural audit of all 11 adapters, mock fixture architectures, edge-case vulnerability assessments, and a complete, production-grade drop-in blueprint for `backend/tests/test_sources.py` that runs **100% offline with zero live network calls and zero external API credentials**.

---

## 2. In-Depth Audit of All 11 External Data Adapters

All adapters reside in `backend/app/services/sources.py`.

```
backend/app/services/sources.py
├── Helper: _headers, get_json, post_json, _CACHE (lines 7-54)
├── 1. Open-Meteo Weather (lines 56-87)
├── 2. NASA POWER Agroclimatology (lines 89-150)
├── Helper: Weather Series Aggregator (lines 153-226)
├── 3. OpenStreetMap Overpass (lines 229-273)
├── 4. WorldPop Catalog (lines 276-293)
├── 5. OpenAQ v3 Air Quality (lines 296-336)
├── 6. Copernicus Data Space STAC (lines 339-380)
├── 7. Humanitarian Data Cube GHSL STAC (lines 382-418)
├── 8. Google Earth Engine Landsat 8/9 (lines 420-498)
├── Metadata: DATASET_CATALOG (lines 500-541)
├── 9. Sentinel-2 STAC Catalog (lines 544-576)
├── 10. Sentinel-2 COG WarpedVRT Reader (lines 578-659)
└── 11. Google Earth Engine Supplementary (lines 662-769)
```

### Detailed Adapter Specifications

| # | Adapter Function | Upstream Target | Auth / Credentials | Parsing & Transformation | Error & Failover Behavior |
|---|---|---|---|---|---|
| **1** | `weather(lat, lon, start=None, end=None)` | `archive-api.open-meteo.com` / `api.open-meteo.com` | None (Public API) | If `start`: ERA5-Land reanalysis with `models="era5_land"`, `soil_moisture_0_to_7cm`. If no `start`: 3-day forecast with `soil_moisture_0_to_1cm` and `current`. | `r.raise_for_status()`. Raises `httpx.HTTPError`. Caught by FastAPI handler -> HTTP 502 Bad Gateway. |
| **2** | `nasa_power(lat, lon, start, end)` | `power.larc.nasa.gov/api/temporal/daily/point` | None (Public API) | Daily agroclimatology (`T2M,RH2M,PRECTOTCORR,WS10M,WD10M,ALLSKY_SFC_SW_DWN`). Maps fill values `<= -999.0` to `None`. | Raises `ValueError` if dates missing or parameter table missing. Upstream error -> HTTP 502. |
| **3** | `osm(lat, lon)` | `overpass-api.de` & `overpass.kumi.systems` | None (Public API) | 1 km radius Overpass QL query. Converts closed ways (>=4 coords, first==last) to GeoJSON `Polygon`; open ways to `LineString`. | Sequential mirror failover: tries primary, records failure in `metadata["endpoint_failures"]`, tries secondary. If both fail, raises `httpx.HTTPError` -> HTTP 502. |
| **4** | `worldpop(country="IND", year=2020)` | `worldpop.org/rest/data/pop/wpgp` | None (Public API) | Filters datasets by ISO3 country and target year (checking `popyear` or `year`). Catalog discovery only. | `r.raise_for_status()`. Upstream error -> HTTP 502. |
| **5** | `air_quality(lat, lon)` | `api.openaq.org/v3` | `OPENAQ_API_KEY` (Header `X-API-Key`) | Queries locations within 25 km (up to 8). For first 5 stations, queries `/v3/locations/{id}/latest`. | Missing key -> `ValueError` (HTTP 422). Discovery failure -> HTTP 502. Individual station failure -> records `id` in `latest_unavailable_location_ids` and continues loop! |
| **6** | `copernicus_catalog(lat, lon, start, end)` | `stac.dataspace.copernicus.eu/v1/search` | None (Discovery only) | POST STAC search for `sentinel-2-l2a` with `eo:cloud_cover <= 20`. Preserves scene metadata, excludes file assets. | Missing dates -> `ValueError` (HTTP 422). Upstream error -> HTTP 502. |
| **7** | `ghsl_catalog(lat, lon)` | `data.humanitariandatacube.org/stac-api` | None (Public STAC) | Bounding box STAC query (`delta=0.05`). Extracts tile `data` asset URL. | If no intersecting tiles -> `ValueError` (HTTP 422). Upstream error -> HTTP 502. |
| **8** | `earth_engine(boundary, start, end)` | Google Earth Engine Client API | `EARTH_ENGINE_PROJECT` + GCP ADC | Merges Landsat LC08/LC09, filters `L2SP`. Masks QA_PIXEL bitmask 63 & QA_RADSAT. Calibrates optical and thermal LST (°C). Samples 500 pixels in EPSG:6933. | Missing env -> `ValueError` (HTTP 422). Empty scenes -> `ValueError` (HTTP 422). |
| **9** | `sentinel_catalog(lat, lon, start, end)` | `earth-search.aws.element84.com/v1` | None (Public STAC) | Bounding box query. Filters `eo:cloud_cover < 20`, sorts ascending. | Upstream error -> HTTP 502. |
| **10** | `sentinel_indices(catalog, lat, lon)` | AWS S3 COG bucket (`sentinel-cogs.s3.us-west-2.amazonaws.com`) | None (Public S3 COG) | Reprojects to EPSG:6933. Warps 32x32 window via `rasterio.vrt.WarpedVRT`. SCL mask (4,5,6,7 valid; clouds NaN). Computes NDVI, NDWI, NDBI. | Empty catalog -> `ValueError`. Host mismatch -> `ValueError` (SSRF protection). |
| **11** | `supplementary_earth_engine(product, boundary, start, end)` | Google Earth Engine Client API | `EARTH_ENGINE_PROJECT` + GCP ADC | Products: `sentinel` (S2 SR HARMONIZED), `modis` (MOD11A2 LST), `worldcover` (ESA 10m), `srtm` (USGS 30m). | Missing env -> `ValueError`. Empty collection -> `ValueError`. Unknown product -> `ValueError`. |

---

## 3. Analysis of Critical Testing Blind Spots & Edge Cases

### 3.1 Blind Spot 1: Open-Meteo Weather (`weather()`)
- **Dual Query Mode**: Archive requires `models="era5_land"`, `start_date`, `end_date`, and `soil_moisture_0_to_7cm`. Forecast requires `forecast_days=3`, `current`, and `soil_moisture_0_to_1cm`.
- **Testing Requirement**:
  - Verify query parameter construction for both modes.
  - Verify response fields: `source` tag distinguishes `"Open-Meteo ERA5-Land"` vs `"Open-Meteo forecast"`.
  - Verify `synthetic == False`.
  - Verify upstream HTTP status error propagates as `httpx.HTTPError`.

### 3.2 Blind Spot 2: OpenAQ v3 (`air_quality()`)
- **Key Vulnerability**: The multi-request nested loop queries `/locations` then sequentially queries `/latest` for up to 5 stations.
- **Testing Requirement**:
  - When `OPENAQ_API_KEY` is not in environment, raises `ValueError`.
  - When discovery succeeds and all stations succeed, `latest_unavailable_location_ids` is empty list `[]`.
  - **Station Fault Tolerance**: When 1 out of 3 stations raises `httpx.HTTPError` (e.g. station deleted upstream), the loop must NOT abort! The failed ID must be recorded in `latest_unavailable_location_ids`, and the remaining 2 stations must be returned in `latest`.
  - When the initial `/locations` discovery call fails, the exception must propagate as `httpx.HTTPError` (triggering 502).

### 3.3 Blind Spot 3: WorldPop Catalog (`worldpop()`)
- **Key Vulnerability**: WorldPop API records have inconsistent year keys (`popyear` vs `year`).
- **Testing Requirement**:
  - Verify filtering by country ISO3 code (`?iso3=IND`).
  - Verify matching against both `"popyear"` and `"year"` attributes.
  - Verify empty dataset list when year does not match.

### 3.4 Blind Spot 4: Humanitarian Data Cube GHSL STAC (`ghsl_catalog()`)
- **Key Vulnerability**: In remote or non-populated coordinates, STAC items may return empty features.
- **Testing Requirement**:
  - Verify bounding box formatting: `lon-0.05,lat-0.05,lon+0.05,lat+0.05`.
  - Verify fallback logic for tile assets: checks `assets["data"]`, falls back to `next(iter(assets.values()))`.
  - When zero tiles intersect, must raise `ValueError("No GHSL population tiles intersect this location...")`.

### 3.5 Blind Spot 5: Sentinel-2 COG WarpedVRT (`sentinel_indices()`)
- **Key Geospatial Complexities**:
  - `pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933")`
  - `rasterio.vrt.WarpedVRT` reading 32x32 window at 100 m resolution.
  - Security whitelist check: `href.startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/")`.
  - SCL masking: discrete classes 4, 5, 6, 7 are valid; 3, 8, 9, 10 are masked to NaN.
  - Scaling: reflectance multiplied by `scale` (0.0001) + `offset` (0.0).
- **Testing Requirement**:
  - SSRF protection test: Assets hosted on non-AWS domain raise `ValueError("Unexpected satellite asset host.")`.
  - Empty catalog test: `catalog["features"] == []` raises `ValueError("No scenes pass the cloud filter...")`.
  - Mock WarpedVRT test: Simulate 32x32 arrays with known reflectance values and SCL classes.
  - All-cloud test: When 100% of pixels are cloud (SCL=9), `valid_pixels == 0`, `mean` is `None`, and no division by zero error occurs.

### 3.6 Blind Spot 6: Google Earth Engine (`earth_engine()` & `supplementary_earth_engine()`)
- **Key Vulnerability**: Requires GCP credentials and Earth Engine project; cannot run against live GEE servers in CI.
- **Testing Requirement**:
  - Missing `EARTH_ENGINE_PROJECT` raises `ValueError`.
  - Mock Earth Engine fluent API: `ee.Initialize`, `ee.Geometry`, `ee.ImageCollection`, `ee.Image`, `ee.Filter`.
  - Empty collection check: `col.size().getInfo() == 0` raises `ValueError("No Landsat scenes available...")`.
  - Supplementary products: Test `"sentinel"`, `"modis"`, `"worldcover"`, `"srtm"`, and unknown product rejection.
  - **Database Serialization Safety**: Verify all mocked `getInfo()` returns provide pure JSON-serializable structures (dicts, lists, primitives) because `save("satellite", result)` writes directly to SQLite JSON columns!

### 3.7 Dual-Mirror Failover Resilience: OSM Overpass (`sources.osm()`)
- **Key Vulnerability**: OpenStreetMap Overpass servers frequently experience 429 rate limits, 504 gateway timeouts, or 406 bad requests.
- **Failover Logic**:
  1. Primary mirror: `https://overpass-api.de/api/interpreter`
  2. Secondary mirror: `https://overpass.kumi.systems/api/interpreter`
- **Testing Requirement**:
  - **Single mirror failure**: Primary fails with `httpx.HTTPError`; secondary succeeds. Verify `result["metadata"]["endpoint_failures"]` logs the primary failure, and features are parsed from the secondary response.
  - **Total mirror failure**: Both mirrors fail with `httpx.HTTPError`. Verify `sources.osm()` raises `httpx.HTTPError` mentioning both mirrors. Under `/api/data/ingest`, FastAPI catches this and returns HTTP 502.

### 3.8 In-Memory Cache Isolation (`sources._CACHE`)
- **Mechanism**: `_CACHE` is a global dict storing `(monotonic_time, result)` keyed by `(method, url, str(params))`.
- **Risk**: A mock response in test A will be returned in test B if they share the same URL/params within 900 seconds!
- **Testing Requirement**: A fixture or test helper must execute `sources._CACHE.clear()` before/after each test.

---

## 4. Mock Architecture & Offline Design Patterns

To ensure 100% offline determinism, test execution without network access, and test speed under 1 second:

### 4.1 HTTP Mocking Strategy
Instead of starting mock HTTP servers or requiring live ports, mock `sources.get_json` and `sources.post_json` directly, or mock `httpx.AsyncClient` via `httpx.MockTransport`.
For unit testing individual functions in `sources.py`, monkeypatching `sources.get_json` / `sources.post_json` provides exact argument inspection (URL, params, headers) and deterministic response injection.

### 4.2 Rasterio & GDAL WarpedVRT Mocking Strategy
`sentinel_indices()` interacts with `rasterio.Env`, `rasterio.open`, and `WarpedVRT`.
We mock `rasterio.open` and `WarpedVRT` as context managers returning 32×32 NumPy arrays:
```python
class MockVRT:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, idx):
        return self.data
```

### 4.3 Google Earth Engine Mocking Strategy
By injecting a mock `ee` module into `sys.modules["ee"]`, the dynamic `import ee` inside `earth_engine()` and `supplementary_earth_engine()` binds to the mock.
Fluent chaining pattern:
```python
mock_ee = MagicMock()
mock_col = MagicMock()
mock_col.merge.return_value = mock_col
mock_col.filterBounds.return_value = mock_col
mock_col.filterDate.return_value = mock_col
mock_col.filter.return_value = mock_col
mock_col.map.return_value = mock_col
mock_col.median.return_value = mock_img
mock_col.mean.return_value = mock_img
mock_col.first.return_value = mock_img
mock_img.sample.return_value.getInfo.return_value = {"type": "FeatureCollection", "features": []}
```

---

## 5. Complete Drop-In Test Blueprint for `backend/tests/test_sources.py`

Below is the complete, drop-in Python code designed for `backend/tests/test_sources.py`. It preserves all 5 existing tests and adds 21 new comprehensive unit tests covering all 11 adapters and edge cases (26 tests total).
