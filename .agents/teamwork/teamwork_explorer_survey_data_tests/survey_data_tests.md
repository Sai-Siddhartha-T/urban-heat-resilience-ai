# Comprehensive Survey Report: Data Adapters, External Integrations & Testing Framework

**Date**: 2026-11-08  
**Author**: Explorer 3 — Data Adapters, External Integrations & Testing Specialist  
**Workspace**: `d:\Urban-Heat-Resilience-AI`  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_data_tests`

---

## 1. Executive Summary

The **AI-Powered Urban Heat Resilience & Mitigation Platform** is architected around a strict data governance and provenance principle:
> **Live external geospatial and meteorological observation layers must remain strictly separated from the synthetic demonstration model.** Remote API errors are never masked by synthetic data, and real-world satellite observations are never silently injected into uncalibrated models without explicit, documented transformation pipelines.

This investigation evaluated all external data adapters, API integrations, data schemas, caching policies, and the complete testing framework across backend, frontend, and end-to-end verification scripts.

### Key Findings:
1. **Rich Adapter Layer with 11 Ingestion Pathways**: The system implements live adapters for Open-Meteo (historical ERA5-Land & 3-day forecast), NASA POWER (daily agroclimatology), OpenStreetMap (Overpass API with mirror failover), WorldPop (STAC/catalog), OpenAQ v3 (station discovery & latest readings), Sentinel-2 STAC (Element 84 Earth Search), Sentinel-2 COG processing (AWS S3 Cloud-Optimized GeoTIFF via `rasterio.vrt.WarpedVRT` and SCL cloud masking), Copernicus Data Space STAC, Humanitarian Data Cube GHSL STAC, Google Earth Engine (Landsat 8/9 L2SP LST, Sentinel-2 harmonized, MODIS MOD11A2, ESA WorldCover, USGS SRTM), and an OpenStreetMap tile cache proxy.
2. **Current Backend Test Suite**: 20 tests across 5 test files in `backend/tests/` (16 originally recorded, 4 added for NASA POWER, Copernicus STAC, and weather series). All 20 tests pass.
3. **Severe Frontend Test Deficit**: While `vitest` is installed as a development dependency in `frontend/package.json` (`"test": "vitest run"`), **there are zero frontend test files** in `frontend/src`. The 2,164-line monolithic `App.tsx` and companion components have 0% automated unit/component test coverage.
4. **Adapter Testing Blind Spots**: Out of 11 ingestion mechanisms, only 4 have unit tests in `test_sources.py` (Sentinel-2 STAC catalog, NASA POWER parsing, Copernicus STAC metadata, and OSM geometry). The Open-Meteo adapter, OpenAQ adapter, WorldPop adapter, GHSL catalog, Sentinel-2 COG raster window reader, and Google Earth Engine adapters currently have **no unit tests or mock fixtures**.
5. **Lifespan Startup Bottleneck in Tests**: The FastAPI application lifespan (`lifespan` in `app/main.py`) trains all 3 ML models (Random Forest, XGBoost, LightGBM with 180 estimators each) and computes TreeSHAP on 324 cells upon startup. Any test using `TestClient(app)` incurs a 20-30s model training overhead on a clean test database.

---

## 2. Comprehensive Inventory of Data Adapters & Integrations

All data adapter implementations reside in `backend/app/services/sources.py` (769 lines), supported by data manipulation utilities in `backend/app/services/data.py` (183 lines) and database persistence in `backend/app/db.py` (84 lines).

### 2.1 Adapter Deep Dives

#### 1. Open-Meteo Weather Adapter (`sources.weather`)
- **Code Location**: `backend/app/services/sources.py:56-87`
- **Endpoints**:
  - Archive (ERA5-Land reanalysis): `https://archive-api.open-meteo.com/v1/archive` (when `start` date provided).
  - Forecast: `https://api.open-meteo.com/v1/forecast` (when `start` is null; defaults to 3-day forecast).
- **Parameters**: `latitude`, `longitude`, `hourly` (`temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m, wind_direction_10m, shortwave_radiation, soil_moisture_0_to_7cm` [or `soil_moisture_0_to_1cm` for forecast]), `timezone="UTC"`.
- **Network Execution**: `httpx.AsyncClient(timeout=45, follow_redirects=True)` via helper `get_json`.
- **Caching**: Global dictionary `_CACHE` with in-memory TTL of 900 seconds (15 minutes). Keyed by `("GET", url, str(params))`.
- **Error Handling & Fallback**: `r.raise_for_status()` raises `httpx.HTTPStatusError`. Caught by FastAPI exception handler in `main.py:129-137`, returning HTTP 502 with: `"External source unavailable. No substitute data was inserted. Retry later."`
- **Rate Limits**: Open-Meteo free tier permits 10,000 daily requests, max 600/minute. No client-side exponential backoff or throttling exists.
- **Persistence**: Persisted via `save("weather", result)` in database `analysis_records`.
- **Series Conversion**: `weather_series(stored)` (`sources.py:153-226`) aggregates hourly points into daily average temperatures, relative humidity, and retrieved-hour counts for visualization.

#### 2. NASA POWER Agroclimatology Adapter (`sources.nasa_power`)
- **Code Location**: `backend/app/services/sources.py:89-150`
- **Endpoint**: `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Parameters**: `parameters="T2M,RH2M,PRECTOTCORR,WS10M,WD10M,ALLSKY_SFC_SW_DWN"`, `community="AG"`, `longitude`, `latitude`, `start` (YYYYMMDD), `end` (YYYYMMDD), `format="JSON"`, `time-standard="UTC"`.
- **Data Parsing (`power_rows`)**: Translates date-keyed dictionaries into sorted daily records. Converts missing/fill values (`fill_value = -999.0`) into `None`.
- **Limitations Enforced**: Notes meteorology resolution is ~0.5° × 0.625° with coarser solar grid; point meteorology only, not land surface temperature, not fed to heat model.
- **Configuration**: Public API, no key required.

#### 3. OpenStreetMap Overpass Adapter (`sources.osm`)
- **Code Location**: `backend/app/services/sources.py:229-273`
- **Endpoints / Mirrors**:
  - Primary: `https://overpass-api.de/api/interpreter`
  - Fallback: `https://overpass.kumi.systems/api/interpreter`
- **Query**: Overpass QL query:
  `[out:json][timeout:25];(way(around:1000,{lat},{lon})[building];way(around:1000,{lat},{lon})[highway];way(around:1000,{lat},{lon})[leisure=park];way(around:1000,{lat},{lon})[natural=water];);out geom 120;`
- **Failover Strategy**: Iterates through `OVERPASS_URLS`. Catches `httpx.HTTPError`, logs endpoint failures to metadata, and tries the next mirror. If all fail, raises `httpx.HTTPError` listing all failed mirrors.
- **Geometry Parsing**: Closed ways (>3 coordinates with identical first and last) converted to GeoJSON `Polygon`; open ways converted to `LineString`. Tags and OSM ID preserved in `properties`.
- **Limits**: 1 km radius, max 120 ways. 25s Overpass timeout, 45s HTTP client timeout.

#### 4. WorldPop Population Catalog Adapter (`sources.worldpop`)
- **Code Location**: `backend/app/services/sources.py:276-293`
- **Endpoint**: `https://www.worldpop.org/rest/data/pop/wpgp?iso3={country}`
- **Scope**: Queries dataset catalog for a country (default `"IND"`) and year (default 2020).
- **Limitation**: Discovery catalog only. Does not download or sample rasters; demographics are not inferred.

#### 5. OpenAQ v3 Air Quality Adapter (`sources.air_quality`)
- **Code Location**: `backend/app/services/sources.py:296-336`
- **Endpoints**:
  - Discovery: `https://api.openaq.org/v3/locations?coordinates={lat},{lon}&radius=25000&limit=8`
  - Readings: `https://api.openaq.org/v3/locations/{location_id}/latest?limit=20`
- **Auth**: Requires `OPENAQ_API_KEY` in environment. Sent via header `X-API-Key`. If missing, raises `ValueError("OPENAQ_API_KEY is not configured; air quality is optional.")`.
- **Fault Tolerance**: Iterates up to 5 nearby stations. If an individual station's latest endpoint fails with `httpx.HTTPError`, it records `location_id` into `unavailable` list and continues without aborting the overall response.

#### 6. Sentinel-2 STAC Catalog Adapter (`sources.sentinel_catalog`)
- **Code Location**: `backend/app/services/sources.py:544-576`
- **Endpoint**: AWS Earth Search STAC API (`https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items`)
- **Query**: Bounding box `[lon-0.02, lat-0.02, lon+0.02, lat+0.02]` (~4.4 km), datetime range, limit 50.
- **Filtering**: Retains scenes with `eo:cloud_cover < 20`, sorted ascending by cloud cover.

#### 7. Sentinel-2 Cloud-Optimized GeoTIFF (COG) Reader (`sources.sentinel_indices`)
- **Code Location**: `backend/app/services/sources.py:578-659`
- **Storage Target**: AWS S3 Public COG bucket: `https://sentinel-cogs.s3.us-west-2.amazonaws.com/`
- **Security Check**: Enforces `href.startswith("https://sentinel-cogs.s3.us-west-2.amazonaws.com/")` to prevent SSRF or arbitrary remote reading.
- **VSI / GDAL Configuration**:
  ```python
  options = {
      "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
      "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
      "GDAL_HTTP_TIMEOUT": "25",
      "GDAL_HTTP_MAX_RETRY": "1",
  }
  ```
  Supports `GDAL_HTTP_PROXY` if `HTTPS_PROXY` env var is set.
- **Raster Processing**:
  - Reprojects point to `EPSG:6933` using `pyproj.Transformer`.
  - Warps 32×32 window at 100 m resolution centered on target using `rasterio.vrt.WarpedVRT`.
  - Reads bands: `red` (B04), `nir` (B08), `green` (B03), `swir16` (B11), and `scl` (Scene Classification Layer).
  - Resampling: Nearest-neighbor for discrete `scl`; average resampling for continuous reflectance bands.
  - SCL Quality Mask: Retains only valid classes 4 (vegetation), 5 (not vegetated), 6 (water), 7 (unclassified). Clouds, shadows, and snow become `NaN`.
  - Radiometric Scaling: Reads asset STAC `raster:bands` scale (default 0.0001) and offset.
  - Computes NDVI, NDWI, NDBI via `app.services.data.spectral_indices`.

#### 8. Copernicus Data Space STAC Adapter (`sources.copernicus_catalog`)
- **Code Location**: `backend/app/services/sources.py:339-380`
- **Endpoint**: `https://stac.dataspace.copernicus.eu/v1/search`
- **Method**: POST JSON search on collection `sentinel-2-l2a`, delta 0.05°, cloud cover ≤ 20%.
- **Limitation**: Public discovery catalog only; scene file downloads require Copernicus user credentials.

#### 9. Humanitarian Data Cube GHSL STAC Adapter (`sources.ghsl_catalog`)
- **Code Location**: `backend/app/services/sources.py:382-418`
- **Endpoint**: `https://data.humanitariandatacube.org/stac-api/collections/jrc_ghsl_pop/items`
- **Method**: GET STAC items by bounding box. Returns tile asset URLs. Rasters are not sampled directly.

#### 10. Google Earth Engine Adapters (`sources.earth_engine` & `sources.supplementary_earth_engine`)
- **Code Location**: `backend/app/services/sources.py:420-498` & `662-769`
- **Credentials**: Requires `EARTH_ENGINE_PROJECT` env var and Google application default credentials (`gcloud auth application-default login` or service account JSON).
- **Core Landsat 8/9 L2SP Flow**:
  - Merges `LANDSAT/LC08/C02/T1_L2` and `LANDSAT/LC09/C02/T1_L2`.
  - Filters by polygon boundary, date range, and `PROCESSING_LEVEL == "L2SP"`.
  - Cloud / Saturation Mask: `(QA_PIXEL & 63) == 0` and `QA_RADSAT == 0`.
  - Radiometric Conversion: Surface reflectance scaled by `0.0000275 - 0.2`; Thermal band `ST_B10 * 0.00341802 + 149 - 273.15` -> LST in °C.
  - Spectral Indices: NDVI, NDWI, NDBI.
  - Samples 500 points in EPSG:6933 at 1000 m scale.
- **Supplementary Products (`supplementary_earth_engine`)**:
  - `sentinel`: `COPERNICUS/S2_SR_HARMONIZED` (SCL 4-7, median composite).
  - `modis`: `MODIS/061/MOD11A2` (Daytime LST 1 km 8-day composite, scaled by 0.02 K - 273.15).
  - `worldcover`: `ESA/WorldCover/v200` (10 m categorical land cover).
  - `srtm`: `USGS/SRTMGL1_003` (30 m elevation in meters).

#### 11. OpenStreetMap Map Tile Proxy (`app.main.map_tile`)
- **Code Location**: `backend/app/main.py:165-186`
- **Endpoint**: `GET /api/tiles/{z}/{x}/{y}.png`
- **Upstream**: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
- **Caching**: In-memory `TILES` dictionary with a 256-tile LRU eviction policy. HTTP response header `Cache-Control: public, max-age=86400`.
- **Attribution & User-Agent**: Enforces User-Agent header `HeatwiseResearchPrototype/0.1`.

---

### 2.2 Adapter Comparison Matrix

| Adapter | Endpoint / Service | Protocol / Format | Auth Required | Cache Mechanism | Error Handling | Fallback Policy | Storage Target |
|---|---|---|---|---|---|---|---|
| **Open-Meteo** | `archive-api.open-meteo.com` / `api.open-meteo.com` | HTTP GET / JSON | None | In-memory 15m TTL | `raise_for_status` | 502 Bad Gateway, strict no-synthetic | `weather` in SQLite/PostGIS |
| **NASA POWER** | `power.larc.nasa.gov` | HTTP GET / JSON | None | In-memory 15m TTL | `raise_for_status`, null fill mapping | 502 Bad Gateway | `weather` in SQLite/PostGIS |
| **OSM Overpass** | `overpass-api.de` & `overpass.kumi.systems` | HTTP GET / Overpass QL | None | In-memory 15m TTL | Dual mirror failover on HTTPError | 502 Bad Gateway if all fail | `osm` in SQLite/PostGIS |
| **WorldPop** | `worldpop.org/rest/data/pop/wpgp` | HTTP GET / JSON | None | In-memory 15m TTL | `raise_for_status` | 502 Bad Gateway | `satellite` in SQLite/PostGIS |
| **OpenAQ v3** | `api.openaq.org/v3` | HTTP GET / JSON | `OPENAQ_API_KEY` | In-memory 15m TTL | Per-station HTTPError tolerance | Skips station, keeps partial results | `monitoring` in SQLite/PostGIS |
| **Sentinel-2 STAC** | `earth-search.aws.element84.com` | HTTP GET / STAC GeoJSON | None | In-memory 15m TTL | `raise_for_status` | 502 Bad Gateway | `satellite` in SQLite/PostGIS |
| **Sentinel-2 COG** | `sentinel-cogs.s3.us-west-2.amazonaws.com` | HTTPS VSI CURL / COG GeoTIFF | None | In-memory 15m TTL (catalog) | Host whitelist, rasterio exceptions | 422 / 500 error | `satellite` in SQLite/PostGIS |
| **Copernicus STAC** | `stac.dataspace.copernicus.eu` | HTTP POST / STAC JSON | None (discovery) | In-memory 15m TTL | `raise_for_status` | 502 Bad Gateway | `satellite` in SQLite/PostGIS |
| **GHSL STAC** | `data.humanitariandatacube.org` | HTTP GET / STAC JSON | None | In-memory 15m TTL | `raise_for_status`, empty check | 422 ValueError if empty | `satellite` in SQLite/PostGIS |
| **Google Earth Engine**| GEE Client API | RPC / Protocol Buffers | GCP ADC & Project ID | None (GEE server-side cache) | `ee.EEException`, empty check | 422 ValueError if not configured | `satellite` in SQLite/PostGIS |
| **OSM Tile Proxy** | `tile.openstreetmap.org` | HTTP GET / PNG | None | In-memory 256 tiles LRU | `raise_for_status` | 502 Bad Gateway | In-memory `TILES` dict |

---

## 3. Current Testing Framework Assessment

### 3.1 Backend Test Suite (`backend/tests/`)

The backend test suite contains **20 tests** across 5 files:

```
backend/tests/
├── conftest.py             # Test environment isolation fixtures
├── test_foundation.py      # Health, synthetic data generation, spectral indices (3 tests)
├── test_pipeline.py        # ML evaluation, SHAP additivity, simulation & optimizer constraints (6 tests)
├── test_ai.py              # LLM provider validation, mock transport, guardrails (1 test)
├── test_api.py             # Integrated workflow, input errors, auth, rate limiting (5 tests)
└── test_sources.py         # Satellite catalog, NASA POWER, weather series, Copernicus, OSM (5 tests)
```

#### Detailed Test Inventory:

1. **`test_foundation.py`** (3 tests):
   - `test_health`: Verifies `/api/health` returns HTTP 200 and database status.
   - `test_synthetic_provenance_and_geometry`: Verifies 324 zones generated, synthetic flag is True, and `lst - rural_reference == observed_suhii`.
   - `test_indices_and_cloud_mask`: Verifies `normalized_difference(0.8, 0.2) == 0.6`, zero-denominator returns NaN, and Landsat QA cloud masking sets cloudy pixels to NaN.

2. **`test_pipeline.py`** (6 tests):
   - `test_models_spatial_evaluation`: Verifies 3 models evaluated (RF, XGB, LGBM), spatial block split (162 train / 54 val / 54 buffer / 54 test), RMSE > 0, and feature list excludes targets.
   - `test_shap_additivity`: Verifies exact TreeSHAP additivity (`shap_base + sum(shap.values) == predicted_suhii`) within 1e-4°C on all 324 cells.
   - `test_simulation_constraints`: Verifies physical bounds: rejecting >100% tree coverage, incompatible cool roofs + roof gardens, water supply limits, and protected land violations.
   - `test_optimizer_constraints_and_infeasibility`: Verifies OR-Tools CP-SAT solution feasibility, water ceiling enforcement, and infeasible scenario detection.
   - `test_convenience_inputs_convert_without_changing_coefficients`: Verifies tree count and roof/road percentage conversions to zone area percentages.
   - `test_risk_is_not_population_only`: Verifies vulnerability component (elderly share) independently affects risk score.

3. **`test_ai.py`** (1 test):
   - `test_provider_schema_and_model_validation`: Uses `httpx.MockTransport` to simulate Groq and Gemini API responses. Tests Pydantic output validation, fact-ID citation checking, and hallucinated number rejection.

4. **`test_api.py`** (5 tests):
   - `test_integrated_workflow`: Full end-to-end API walkthrough: overview -> zone prediction -> SHAP explanation -> risk recalculation -> scenario simulation -> CP-SAT optimization -> AI chat -> report generation & download.
   - `test_input_errors`: Verifies HTTP 422 for coordinates out of bounds, reversed dates, non-Polygon boundaries, negative intervention coverage, and non-existent zones (HTTP 404).
   - `test_unconfigured_provider_fallback`: Del-envs provider keys, verifies auto fallback to local template with provider failure logs.
   - `test_api_token`: Verifies Bearer token security middleware (HTTP 401 without token, 200 with valid token).
   - `test_upstream_failure_is_explicit`: Mocks `sources.weather` to raise `httpx.ConnectError`, asserting HTTP 502 and message `"No substitute data"`.

5. **`test_sources.py`** (5 tests):
   - `test_catalog_filters_clouds_and_preserves_dates`: Mocks `get_json` to test Sentinel-2 STAC filtering cloud cover <20%.
   - `test_power_rows_keep_missing_fill_values`: Tests NASA POWER fill value (-999.0) mapping to `None`.
   - `test_weather_series_uses_only_retrieved_hours`: Tests Open-Meteo hourly aggregation to daily averages, omitting null readings.
   - `test_copernicus_keeps_catalog_metadata_only`: Tests Copernicus STAC POST query and metadata extraction.
   - `test_osm_geometry_conversion`: Tests Overpass elements conversion to GeoJSON Polygon.

---

### 3.2 Frontend Testing Status

- **Status**: **Completely Missing (0 tests)**.
- `package.json` includes `"vitest": "^3.2.0"` and `"test": "vitest run"`.
- However, `Get-ChildItem -Recurse frontend\src -Filter "*test*"` returns **zero test files**.
- The frontend codebase has:
  - `frontend/src/App.tsx` (2,164 lines)
  - `frontend/src/api.ts` (55 lines)
  - `frontend/src/components/HeatMap.tsx` (134 lines)
  - `frontend/src/components/BoundarySketch.tsx` (95 lines)
  - `frontend/src/components/button.tsx` (37 lines)
- **Zero test coverage** exists for React component rendering, user interactions, leaflet map layers, form validation, API client error parsing, or state management.

---

### 3.3 End-to-End Automation & Smoke Testing

- **Script**: `scripts/browser_smoke.py` (56 lines).
- **Tool**: Playwright Chromium automation (`executable_path=os.getenv('BROWSER_EXECUTABLE', '/usr/bin/chromium')`).
- **Workflows Verified**:
  1. Overview map loading and 324 interactive Leaflet cells rendered.
  2. Prediction charts and model comparison cards.
  3. Explainable AI (SHAP waterfall/bar breakdown).
  4. Heat risk recalculation with adjusted hazard/exposure/vulnerability weights.
  5. Intervention simulator scenario creation and constraint validation.
  6. Constrained optimization execution (CP-SAT solver).
  7. Local evidence assistant chat.
  8. Analysis report generation and CSV download validation (>1000 bytes).
  9. City switching (Ahmedabad -> Delhi -> Ahmedabad) and map badge updates.
  10. Mobile viewport responsive layout (390×844) with sidebar drawer toggle and no horizontal overflow (`scrollWidth <= innerWidth`).
- **Artifacts Saved**: `work/overview-desktop.png`, `work/simulator-desktop.png`, `work/overview-mobile.png`, `work/browser-export.csv`.

---

## 4. Test Coverage Gaps & Risk Analysis

### 4.1 Data Adapter Unit Test Gaps

| Adapter / Component | Missing Test Scenarios | Impact / Risk |
|---|---|---|
| **Open-Meteo** (`sources.weather`) | - Archive vs forecast query parameter branch.<br>- Hourly variable replacement (`soil_moisture_0_to_1cm` vs `7cm`).<br>- Upstream HTTP 429 rate limit or 500 error propagation.<br>- Handling empty or malformed hourly JSON. | Medium: Core weather ingestion is untested in unit isolation; regression could break `/api/data/ingest`. |
| **OpenAQ v3** (`sources.air_quality`) | - `OPENAQ_API_KEY` missing ValueError check.<br>- Auth header `X-API-Key` verification.<br>- Location discovery parsing.<br>- Station failure isolation (verifying loop continues when 1 station fails). | High: OpenAQ adapter has complex multi-request logic and partial error handling that is completely untested. |
| **WorldPop** (`sources.worldpop`) | - ISO3 parameter passing.<br>- Year filtering logic (`popyear` vs `year`).<br>- Catalog response mapping. | Low: Simple catalog retrieval, but untested. |
| **GHSL Catalog** (`sources.ghsl_catalog`) | - Bounding box string formatting.<br>- Asset extraction fallback (`assets.get("data") or next(iter(assets.values()))`).<br>- Empty tile result ValueError exception. | Medium: Uncovered edge cases when location has no overlapping population tiles. |
| **Sentinel-2 COG** (`sources.sentinel_indices`) | - Host whitelist validation (rejecting non-AWS S3 sentinel hosts).<br>- `WarpedVRT` window reading and reprojection.<br>- SCL mask filtering (classes 4-7 kept, others NaN).<br>- STAC scale/offset application.<br>- Empty feature list exception. | High: Most complex geospatial code in project (GDAL VSI, WarpedVRT, rasterio). Zero unit tests with mock rasters. |
| **Google Earth Engine** (`sources.earth_engine`) | - Missing credentials exception.<br>- Landsat LC08/LC09 collection merging.<br>- Cloud masking bitwise logic (`QA_PIXEL & 63 == 0`).<br>- Thermal band Celsius conversion.<br>- Supplementary products (MODIS, WorldCover, SRTM). | High: GEE code has intricate EE expressions that are never validated in CI because GEE credentials are not in CI. Needs mock EE fixtures. |
| **OSM Overpass Failover** (`sources.osm`) | - Primary mirror failure (`overpass-api.de` returning 406/504) triggering fallback to `overpass.kumi.systems`.<br>- Both mirrors failing raising `httpx.HTTPError`.<br>- Radius and tag filtering. | High: Dual-mirror failover is a key resilience feature, but existing test only tests single mock without exercising the failover loop. |
| **In-Memory Cache** (`_CACHE`) | - 900s TTL expiration logic.<br>- Cache hit avoiding network call.<br>- Cache key collisions or mutation. | Medium: In-memory cache is shared across all adapters without thread locks; potential race conditions. |
| **Map Tile Proxy** (`map_tile`) | - Coordinate range validation (negative z, out-of-bounds x, y).<br>- LRU eviction when cache exceeds 256 tiles.<br>- Upstream tile server error handling. | Low: Simple proxy, but bounds validation needs explicit test cases. |

### 4.2 API & Middleware Test Gaps

1. **Rate Limiting Middleware**: `main.py:108-117` implements a sliding window rate limiter (180 requests per minute per IP). No test verifies that 181 requests trigger HTTP 429.
2. **Database Persistence**: No test verifies SQLite vs PostGIS boundary storage differences (`WKT` with SRID 4326 vs GeoJSON string in `Zone.boundary`).
3. **Data Records Filtering & Status**: `/api/data/status` and `/api/data/records?kind=...` have no dedicated tests asserting schema and pagination.
4. **Report Downloads**: While `/api/reports/generate` is called in `test_integrated_workflow`, PDF generation (`reportlab` if used, or HTML/markdown conversion) and error states on invalid report IDs are only partially tested.

### 4.3 Architecture & Runtime Inefficiencies in Testing

1. **Lifespan Startup Overhead**: `lifespan` in `app/main.py` runs `await asyncio.to_thread(state, "Ahmedabad")` on startup, training 3 models (540 trees total) and calculating TreeSHAP on 324 cells.
   - In production, this pre-warms the cache.
   - In testing, **every single test file or fixture that spins up `TestClient(app)` waits 20-30 seconds** for full model training, even if the test is just checking `/api/health` or `/api/tiles`!
   - Recommendation: Add a test configuration or environment variable (e.g. `TESTING=1` or `WARM_CACHE=0`) to skip lifespan training during fast unit tests.
2. **Matplotlib Config Warning**: Tests and Python invocations output:
   `Matplotlib created a temporary cache directory at ... because C:\Users\siddh\.matplotlib is not a writable directory`.
   `MPLCONFIGDIR` is set in `conftest.py`, but when running commands directly or before conftest executes, the warning appears.

---

## 5. End-to-End Testing Track Proposal (Tiers 1–4 Framework)

To guarantee software resilience, complete integration verification, and eliminate blind spots, an end-to-end testing track structured into four distinct verification tiers must be established:

```
┌─────────────────────────────────────────────────────────────────┐
│               TIER 4: Real-World Scenarios                      │
│   - Browser E2E (Playwright)  - Upstream Network Chaos Testing   │
│   - Multi-City Concurrency    - Real Labeled GeoJSON Import CLI │
├─────────────────────────────────────────────────────────────────┤
│            TIER 3: Cross-Feature Integration Workflows          │
│   - Ingest -> Predict -> SHAP -> Risk -> Optimize -> Export     │
│   - LLM Failover Cascade (Groq -> Gemini -> Local Summary)      │
│   - State Isolation & Persistence Verification                  │
├─────────────────────────────────────────────────────────────────┤
│               TIER 2: Boundary & Corner Cases                   │
│   - Coordinate / Date Bounds  - Zero Denominators / NaNs        │
│   - Infeasible Interventions  - 180 req/min Rate Limit Breach   │
│   - Overpass Failover Loops   - Cloud Cover Edge Cases (0%/100%)│
├─────────────────────────────────────────────────────────────────┤
│               TIER 1: Feature Coverage (Unit)                   │
│   - Adapter Parsers (All 11)  - ML Holdout Math (R2/RMSE/MAE)   │
│   - Schema Strict Validation  - Frontend Vitest Components     │
└─────────────────────────────────────────────────────────────────┘
```

---

### Tier 1: Feature Coverage (Unit & Subsystem Testing)

**Objective**: Verify that every individual module, parser, schema validator, and UI component functions correctly in complete isolation with deterministic fixtures.

1. **Data Adapter Parsers**:
   - `test_weather_archive_params`: Verify Open-Meteo archive parameters include `models="era5_land"`, `start_date`, `end_date`.
   - `test_weather_forecast_params`: Verify Open-Meteo forecast parameters include `forecast_days=3`, `current`, `soil_moisture_0_to_1cm`.
   - `test_openaq_station_parsing`: Provide mock OpenAQ v3 location and latest measurement JSON; verify extraction of station IDs, pollutant values, and unit tags.
   - `test_worldpop_catalog_parsing`: Provide mock WorldPop catalog response; verify filtering by target year and country ISO3.
   - `test_ghsl_catalog_parsing`: Provide mock Humanitarian Data Cube STAC items; verify tile bounding box and asset URL extraction.
   - `test_sentinel_indices_math`: Provide synthetic numpy band arrays (`red`, `nir`, `green`, `swir16`, `scl`); verify exact output of NDVI, NDWI, NDBI and valid pixel masking.
   - `test_tile_cache_bounds`: Verify tile coordinate math across zoom levels 0 to 18.
2. **Schema & Validation**:
   - Verify `StrictModel` rejects unknown fields (`extra="forbid"`).
   - Verify `AreaRequest.validate_area`: latitude/longitude pairing, start/end date ordering, maximum 366-day range, GeoJSON Polygon geometry validity, and max 4 square degrees area.
   - Verify `SimulationRequest` and `OptimizationRequest` numerical limits.
3. **Frontend Vitest Component Tests**:
   - `Button.test.tsx`: Verify rendering variants (`primary`, `secondary`, `destructive`), loading spinners, and disabled state.
   - `api.test.ts`: Mock `fetch`; verify session storage token header attachment, JSON parsing, and HTTP error unwrapping.
   - `HeatMap.test.tsx`: Mock Leaflet map container; verify GeoJSON layer binding and hover tooltip callbacks.
   - `BoundarySketch.test.tsx`: Verify coordinate sketch parsing and polygon closure.

---

### Tier 2: Boundary & Corner Cases

**Objective**: Stress-test the application against malformed inputs, physical/mathematical edge conditions, rate limits, and network anomalies.

1. **Geospatial & Mathematical Boundaries**:
   - Polar coordinates (`lat = 80.0`, `lon = 180.0`) and coordinate edge wrapping.
   - Cosine longitude scaling at extreme latitudes: verify width computation in `sample_data` avoids division by zero or infinite width (`math.cos(math.radians(lat))`).
   - Zero-denominator normalized difference: verify `normalized_difference(0, 0)` returns `NaN` without division-by-zero warnings.
   - Radiometric edge cases: all-cloud scenes (`scl` array with no classes in 4..7); verify `sentinel_indices` returns `valid_pixels = 0` and `mean = None` without crashing.
   - SCL boundary values: verify classes 3 (cloud shadow), 8 (cloud medium prob), 9 (cloud high prob), 10 (cirrus), 11 (snow) are strictly masked out.
2. **Network & System Fault Boundaries**:
   - Overpass primary mirror failure: Mock `overpass-api.de` returning HTTP 406 and 504; verify seamless failover to `overpass.kumi.systems`.
   - Overpass total failure: Mock both mirrors failing; verify HTTP 502 with composite error description.
   - OpenAQ partial station failure: 2 out of 5 stations return HTTP 404/500; verify remaining 3 stations succeed and failed IDs recorded in `latest_unavailable_location_ids`.
   - Rate limiting breach: Dispatch 181 rapid requests to `/api/health`; verify request 181 receives HTTP 429 `"Rate limit reached. Retry in one minute."`.
   - Token security: Test requests with invalid bearer token, malformed authorization headers, and token bypass attempts on non-tile routes.

---

### Tier 3: Cross-Feature Integration Workflows

**Objective**: Verify end-to-end data flow across multiple modules and services.

1. **Full Decision Pipeline Workflow**:
   - Step 1: Ingest live weather from Open-Meteo for Ahmedabad.
   - Step 2: Ingest live Sentinel-2 STAC catalog.
   - Step 3: Trigger model training on synthetic grid -> verify LightGBM/XGBoost/RF evaluation metrics and winning model selection.
   - Step 4: Request zone prediction and TreeSHAP explanation for highest heat zone (`Sector 09 · 09`). Verify exact SHAP additivity.
   - Step 5: Recalculate risk with custom weights (`hazard=2.0, exposure=1.0, vulnerability=2.5`). Verify priority ranking shifts toward high-elderly zones.
   - Step 6: Configure scenario with cool roofs (15%) and urban trees (10%). Verify feasibility check and cooling estimation.
   - Step 7: Run OR-Tools CP-SAT optimizer across top 5 priority zones with water ceiling (500 m³/day). Verify CP-SAT returns `OPTIMAL` or `FEASIBLE` and total water used ≤ 500.
   - Step 8: Send zone facts and optimization results to AI Chat assistant. Verify fallback cascading (Groq -> Gemini -> local template) and schema enforcement.
   - Step 9: Export analysis report in JSON, CSV, and Markdown. Verify integrity of all downloaded files.
2. **Multi-City Concurrency & State Isolation**:
   - Concurrently query and update Ahmedabad, Delhi, and Hyderabad.
   - Verify `threading.RLock` prevents race conditions in `STATE`.
   - Verify records persisted in `analysis_records` and `zones` tables do not leak across city identifiers.

---

### Tier 4: Real-World Application Scenarios (E2E & Resilience)

**Objective**: Validate real-world deployment reliability, browser rendering, user interactions, and failure recovery.

1. **Automated Playwright Browser E2E**:
   - Expand `scripts/browser_smoke.py` into a full Playwright test suite (`frontend/e2e/`):
     - Desktop resolution (1512×1100) and Mobile resolution (390×844).
     - Interactive map clicks and polygon selection.
     - Modal data ingestion workflow: selecting Open-Meteo, submitting coordinates, verifying toast notification.
     - Model retraining button: testing progress spinner and query invalidation.
     - Responsive mobile drawer navigation: testing hamburger click, tab navigation, and auto-close.
     - Console error assertions: zero uncaught JavaScript exceptions.
2. **Real-Data Import CLI Verification**:
   - Execute `python backend/train.py --city Ahmedabad --input <labeled_geojson>`.
   - Test validation of 180+ required cells, WGS84 CRS, required features, and east-west spatial block distribution.
   - Verify external trained models are saved under `<city>-external.joblib` to prevent corrupting demonstration models.
3. **Upstream Network Chaos Injection**:
   - Simulate high latency (5000ms delay on external APIs).
   - Simulate DNS resolution failure for external hostnames.
   - Verify application preserves existing data, returns clear HTTP 502/504 errors, and remains responsive without crashing or deadlocking.

---

## 6. Actionable Recommendations for Implementation Teams

### 6.1 Backend & Adapters (Worker 1 / Milestone 4)
1. **Expose Missing Adapters in Frontend**:
   - `NASA POWER`, `Copernicus STAC`, and `GHSL STAC` are fully implemented in `backend/app/services/sources.py` but missing from the UI dropdown in `frontend/src/App.tsx:2004-2024`. Add these options to the modal.
2. **Optimize Lifespan Startup for Fast Testing**:
   - In `backend/app/main.py:84`, gate `await asyncio.to_thread(state, "Ahmedabad")` behind an environment check (`if os.getenv("PREWARM_STATE", "1") == "1": ...`). In `tests/conftest.py`, set `PREWARM_STATE="0"`. This will cut test startup time from 25s to 0.5s!
3. **Adapter Resilience Enhancements**:
   - Add exponential backoff retry (e.g. using `tenacity` or a simple async retry helper) for Open-Meteo and Overpass APIs to handle intermittent rate limits.
   - Thread-protect the in-memory `_CACHE` dictionary or upgrade to an async LRU cache with TTL.

### 6.2 Testing Framework (Testing Track / Milestone 5)
1. **Build Mock Fixture Library**:
   - Create `backend/tests/fixtures/` containing static mock JSON files for:
     - Open-Meteo archive and forecast responses.
     - OpenAQ v3 location and latest readings.
     - WorldPop catalog response.
     - Copernicus STAC search response.
     - GHSL STAC item response.
     - Overpass ways JSON.
2. **Add Missing Adapter Unit Tests**:
   - Create `backend/tests/test_adapters_deep.py` implementing unit tests for all uncovered adapters using `monkeypatch` and the mock fixture library.
3. **Initialize Frontend Unit Testing**:
   - Create `frontend/vitest.config.ts`.
   - Install `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom`.
   - Add unit tests for `frontend/src/api.ts` and core modular components.

---

## 7. Evidence Citations & Code References

- **Live Data Adapters**: `backend/app/services/sources.py:1-769`
  - Open-Meteo Weather: lines 56–87
  - NASA POWER: lines 89–150
  - Weather Time-Series Aggregation: lines 153–226
  - OpenStreetMap Overpass: lines 229–273
  - WorldPop: lines 276–293
  - OpenAQ v3: lines 296–336
  - Copernicus Data Space STAC: lines 339–380
  - Humanitarian Data Cube GHSL STAC: lines 382–418
  - Google Earth Engine Landsat 8/9: lines 420–498
  - Dataset Catalog Metadata: lines 500–541
  - Sentinel-2 STAC Catalog: lines 544–576
  - Sentinel-2 Cloud-Optimized GeoTIFF (COG) WarpedVRT: lines 578–659
  - Earth Engine Supplementary (Sentinel, MODIS, WorldCover, SRTM): lines 662–769
- **Data Persistence & Database**: `backend/app/db.py:1-84`
- **Data Schemas & Validators**: `backend/app/schemas.py:1-184`
- **API Routing & Ingestion Endpoints**: `backend/app/main.py:1-602`
  - Tile Cache Proxy: lines 165–186
  - Ingestion Dispatcher (`/api/data/ingest`): lines 250–319
- **Backend Tests**: `backend/tests/` (5 files, 20 passing tests)
- **Frontend Source Code**: `frontend/src/` (2,164-line monolithic `App.tsx`, `api.ts`, `BoundarySketch.tsx`, `HeatMap.tsx`, `button.tsx`)
- **Automated Smoke Test**: `scripts/browser_smoke.py:1-56`
