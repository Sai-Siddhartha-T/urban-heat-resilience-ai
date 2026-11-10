# Technical Exploration & Architecture Analysis: Survey 2

**Domain**: Earth Observation, Real Satellite Data Pipelines, Environmental Ingestion & Backend Architecture  
**Focus Requirements**: R2 (Earth Observation & Satellite Pipeline), R3 (Live Weather, Air Quality & Groundwater Ingestion), R7 (Backend Architecture, Typed API Contracts & Grounded AI Assistant)  
**Assigned Agents**: Agent 1 (Satellite Data & Earth Observation Engineer), Agent 6 (Backend Architecture, API & Database Engineer)  
**Date**: 2026-11-10  
**Investigator**: Teamwork Explorer (Survey 2)

---

## 1. Executive Summary

A comprehensive, read-only technical exploration of the Heatwise platform backend was conducted to assess the codebase against requirements **R2**, **R3**, and **R7**.

### Core Findings:
1. **Satellite Pipeline Foundation (R2)**:
   - Google Earth Engine (GEE) integration exists in `backend/app/services/satellite.py` for Landsat 8/9 Collection 2 L2 (ST_B10 thermal scaling, QA_PIXEL bitmasking, QA_RADSAT saturation filter) and Sentinel-2 / MODIS / WorldCover / SRTM.
   - For Sentinel-2, a secondary direct COG windowing reader exists via Element 84 Earth Search STAC API using `rasterio` + `WarpedVRT` directly from AWS S3 without GEE credentials.
   - **Critical Gaps in R2**:
     - *No non-GEE Landsat reader*: Landsat lacks a direct STAC/COG reader (unlike Sentinel-2). If GEE is unconfigured, Landsat fails.
     - *Silent Synthetic Masquerading in Fallback*: When GEE fails or is unconfigured, `fetch_landsat8()` calls `synthetic_satellite_fallback()`, returning hardcoded mock numbers (`lst: 33.5`, `ndvi: 0.45`). This violates the core acceptance criterion: *"No synthetic or placeholder data silently enters real-data results; external services without configured credentials degrade gracefully with clear no-data indicators."*
     - *Absence of Zonal Aggregation*: Neither `satellite.py` nor `geospatial.py` contains a zonal statistics engine to aggregate raster pixels across municipal administrative zones/wards.
     - *Missing Analysis Dataset Bridge*: All ingested live assets in `backend/app/routes/data.py` are saved with `metadata["analysis_ready"] = False`. No pipeline exists to fuse ingested assets into an analysis-ready training dataset, leaving normal analytical mode permanently blocked (HTTP 409).
2. **Live Environmental Ingestion (R3)**:
   - **Open-Meteo**: Operational for hourly and daily forecast/archive meteorology (`sources.weather`). Properly tagged with `kind="modelled"`.
   - **OpenAQ v3**: Operational for location queries, but **critically broken for layer rendering**:
     - Station distance from city center is never calculated.
     - Individual pollutants (PM2.5, PM10, NO2, SO2, O3, CO) are not parsed or normalized.
     - Output payload uses `{"locations": ..., "latest": ...}` instead of `{"stations": [...]}` expected by `backend/app/services/evidence.py:228`, causing air quality map layers to always evaluate to empty/unavailable.
     - Missing OpenAQ credentials trigger an unhandled `ValueError` -> HTTP 422 instead of a graceful `unavailable` status with setup instructions.
     - CPCB direct API / CAAQMS network is unintegrated.
   - **Groundwater (CGWB / India-WRIS)**: **Completely missing**. In `backend/app/services/sources.py`, there is zero implementation of a groundwater adapter, despite layer definitions existing in `evidence.py` and `db.py`.
3. **Backend Architecture & Stability (R7)**:
   - FastAPI structure is cleanly decomposed into 9 APIRouters under `backend/app/routes/` with unified re-exports in `backend/app/routes/__init__.py`.
   - Database layer in `app/db.py` supports dual-engine execution (PostgreSQL/PostGIS with GeoAlchemy2 and SQLite fallback), atomic asset persistence via `persist_acquisition()`, and schema migrations via `app/migrations.py`.
   - **Test Suite Breakdown (365 tests)**:
     - 251 tests pass, 97 fail, 17 error.
     - `test_satellite.py` (24/24) and `test_sources.py` (34/34) pass 100%.
     - Primary cause of failures: Mode resolution in `app/services/state.py` defaults strictly to `mode="normal"` and ignores the `HEATWISE_DEMO_MODE=1` environment variable. When normal mode has no analysis-ready dataset, `state("Ahmedabad")` raises HTTP 409, breaking legacy test suites expecting demo defaults.
     - Primary cause of 17 errors: Python 3.14 Windows binary crash (access violation) when calling OR-Tools CP-SAT solver in `test_optimization.py`.

---

## 2. Requirement-by-Requirement Analysis

### R2: Earth Observation and Real Satellite Data Pipeline
| Component | Requirement Specification | Current Implementation Status | Evaluation & Gap |
|---|---|---|---|
| **Landsat 8/9 Ingestion** | Ingest Landsat 8/9 Collection 2 Level-2 Surface Temperature rasters with USGS scaling | `satellite.py:160-245` (`earth_engine`), `geospatial.py:348-373` (`landsat_lst_from_dn`) | Implemented via GEE with correct USGS scaling (`ST_B10 * 0.00341802 + 149.0 - 273.15`). **Gap**: Missing direct open STAC/COG reader (AWS/Planetary Computer) when GEE is unavailable. |
| **Sentinel-2 Ingestion** | Sentinel-2 Level-2A spectral indices (NDVI, NDWI, NDBI) | `satellite.py:251-370` (`sentinel_catalog`, `sentinel_indices`), `geospatial.py:283-311` | Implemented via both Element 84 Earth Search STAC + S3 COG WarpedVRT windowing and GEE. Accurately calculates NDVI, NDWI, NDBI. Documents NDBaI non-commensurability caveat. |
| **Supplementary EO** | MODIS MOD11A2, ESA WorldCover, NASA SRTM | `satellite.py:419-523` (`supplementary_earth_engine`) | Implemented in GEE for MODIS (1km LST, QC_Day filtering), WorldCover (10m land cover), SRTM (30m elevation). Requires GEE credentials. |
| **Spatial Clipping & Masking** | Spatial clipping, cloud masking, QA filtering | `geospatial.py:landsat_c2_qa_mask`, `satellite.py:clean_landsat`, `satellite.py:sentinel_indices` | Correct QA_PIXEL bitmasking (bits 0..5), QA_RADSAT saturation filter, SCL classes 4-7. `geospatial.py:clip_raster_by_geometry` wraps `rasterio.mask`. |
| **Zone Aggregation** | Spatial aggregation into analytical zones | **NOT IMPLEMENTED** | **Critical Gap**: No zonal statistics function exists to calculate zone-level means/medians across ward polygons from raster grids. |
| **LST vs Air Temp vs Predictions** | Distinctly separate surface temperature from air temperature and model predictions | `evidence.py:LAYER_SPECS`, `provenance.py` | Clearly separated in layer specifications: LST (`observed`), air temp (`modelled`), predictions (`predicted`). |
| **Target City Selection** | Select primary target city based on satellite data coverage and available stations | `data.py:CITIES` | Defined for Ahmedabad, Delhi, Hyderabad. **Recommendation**: Ahmedabad is the primary target city based on HAP benchmark, pre-monsoon cloud-free satellite availability, and ground monitoring. |
| **Degraded Operation** | Graceful degradation without synthetic masquerading | `satellite.py:synthetic_satellite_fallback` | **VIOLATION**: When GEE is unconfigured, fallback returns mock floats. Must be replaced with clean `status="unavailable"` no-data state. |

---

### R3: Live Weather, Air Quality, and Groundwater Ingestion
| Component | Requirement Specification | Current Implementation Status | Evaluation & Gap |
|---|---|---|---|
| **Open-Meteo Weather** | Current weather, daily forecasts, historical trends with actual timestamps | `sources.py:63-94` (`weather`), `sources.py:160-234` (`weather_series`) | Implemented cleanly. Calls Open-Meteo forecast API (current + 3 days) or archive (ERA5-Land). Timestamps preserved. Tagged as `kind="modelled"`. |
| **OpenAQ / CPCB Air Quality** | PM2.5, PM10, NO2, SO2, O3, CO with timestamps and station distance | `sources.py:303-343` (`air_quality`) | **Partial & Broken for Map Rendering**: Ingests OpenAQ v3 `/locations` and `/locations/{id}/latest`. **Gaps**: Does not compute station distance; does not parse individual pollutants; payload format lacks `"stations"` key required by `evidence.py:228`; CPCB direct integration is missing; missing API key causes 422 error instead of clean unavailable status. |
| **CGWB / India-WRIS Groundwater** | Groundwater depth and trends | Defined in `evidence.py:28` & `db.py:31` | **NOT IMPLEMENTED**: Zero adapter code exists in `sources.py`. Missing from `AreaRequest.source` enum. |
| **Differentiating Data Types** | Observations vs forecasts; station readings vs spatial interpolation; groundwater vs soil moisture | `provenance.py`, `evidence.py` | Partially addressed in provenance metadata (`kind`, `status`, `coverage`). Needs explicit API responses preventing confusion between groundwater table depth (mbgl) and surface soil moisture (m³/m³). |
| **Credential Handling** | Graceful no-data handling and setup instructions rather than fabricating measurements | Exception handlers in `main.py` | **Gap**: Missing API keys throw `ValueError`, converted to 422 error. Needs structured 200/503 response with `status="unavailable"` and `setup_instructions`. |

---

### R7: Backend Architecture, Typed API Contracts, and Grounded AI Assistant
| Component | Requirement Specification | Current Implementation Status | Evaluation & Gap |
|---|---|---|---|
| **FastAPI Structure** | Clean service separation, modular routers | `main.py`, `app/routes/*` (9 routers) | Well-structured. Modular APIRouters in `app/routes/`. Clear separation between routes, services, schemas, and db. |
| **Pydantic Validation** | Strict typed validation | `schemas.py`, `schemas/evidence.py`, `schemas/ai.py` | Strict validation (`extra="forbid", allow_inf_nan=False`). **Minor cleanup needed**: Coexistence of `schemas.py` and `schemas/` directory via `__path__` trick. |
| **Database Architecture** | PostgreSQL/PostGIS with explicitly labelled SQLite dev fallback | `app/db.py`, `app/migrations.py` | Fully functional dual-engine with GeoAlchemy2 and SQLite fallback. Clean table models (`analysis_records`, `zones`, `data_assets`, `schema_migrations`). |
| **Structured Logging** | Production-ready structured logging | `main.py`, `logging.getLogger` | Basic logging configured. Needs unified structured log formatting with timestamps, levels, and request context. |
| **Exception Handling** | Centralized exception handling | `main.py:91-106` | Centralized handlers for `ValueError` (422), `httpx.HTTPError` (502), `Exception` (500). |
| **Caching** | Multi-tier caching | `sources.py` (_CACHE), `state.py` (DEMO_STATE/REAL_STATE), `main.py` (TILES), `ml.py` (joblib) | In-memory HTTP cache (900s), thread-safe state cache, tile cache, disk model cache. |
| **Health Checks** | Health check endpoints | `main.py:108-128` (`/api/health`, `/health`), `routes/data.py:37-67` (`/api/data/status`) | Implemented. Returns database engine, synthetic mode, analysis readiness, schema revision, provider status, catalog, and asset counts. |
| **Grounded AI Assistant** | Grounded in actual backend data with citations | `app/routes/ai.py`, `app/services/ai.py` | Implemented with Groq/Gemini multi-provider failover, local heuristic fallback, and citation validation against actual backend facts. |

---

## 3. Deep Dive: Current Satellite Pipeline Inspection

### 3.1 Landsat 8/9 Level-2 Pipeline
- **Implementation Location**: `backend/app/services/satellite.py:160-245` (`earth_engine`), `geospatial.py:348-373` (`landsat_lst_from_dn`).
- **Data Source**: USGS Landsat Collection 2 Level-2 Science Products (`LANDSAT/LC08/C02/T1_L2` and `LANDSAT/LC09/C02/T1_L2`).
- **Processing Chain**:
  1. Image Collection filtering by geometry boundary, date range, and processing level (`L2SP` - Surface Reflectance / Surface Temperature).
  2. Cloud & Shadow Masking via `QA_PIXEL`: Bits 0 to 5 (bitmask 63) checked:
     - Bit 0: Fill
     - Bit 1: Dilated Cloud
     - Bit 2: Cirrus
     - Bit 3: Cloud
     - Bit 4: Cloud Shadow
     - Bit 5: Snow
  3. Radiometric Saturation Filtering via `QA_RADSAT`: Valid pixels must have saturation flag equal to 0.
  4. Physical Units Conversion:
     - Band 10 (Thermal): `ST_B10 * 0.00341802 + 149.0 - 273.15` -> Land Surface Temperature in °C.
     - Bands 3, 4, 5, 6 (Optical): `SR * 0.0000275 - 0.2` -> Unitless surface reflectance [0, 1].
  5. Spectral Index Computation: NDVI, NDWI, NDBI calculated via normalized difference formulas.
- **Vulnerabilities / Gaps**:
  - Requires Google Earth Engine credentials. When unconfigured, it falls back to `synthetic_satellite_fallback()` in `satellite.py:596`, generating synthetic numbers instead of clean no-data indicators.
  - No direct open STAC reader for Landsat (e.g., Planetary Computer or AWS Landsat Collection 2 COGs via rasterio).
  - Only generates 500 point samples or an area-wide mean; does not aggregate into analytical city zones/wards.

### 3.2 Sentinel-2 Level-2A Pipeline
- **Implementation Location**: `backend/app/services/satellite.py:251-370` (`sentinel_catalog`, `sentinel_indices`).
- **Data Source**: Element 84 Earth Search STAC API (`https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items`) and AWS S3 Sentinel COG repository.
- **Processing Chain**:
  1. STAC search with bounding box and date range, filtering scenes with `eo:cloud_cover < 20%`.
  2. COG Window Reading: Uses `rasterio` and `WarpedVRT` to project bounding window into `EPSG:6933` (equal-area metric projection) at 100m grid resolution (32x32 pixels = 3.2 km × 3.2 km).
  3. SCL Masking: Masks non-valid pixels using Scene Classification Layer (SCL); keeps only classes 4 (vegetation), 5 (non-vegetated), 6 (water), 7 (unclassified).
  4. Scale & Offset: Multiplies by scale factor 0.0001 to convert digital numbers to surface reflectance.
  5. Computes NDVI, NDWI, NDBI.
- **Vulnerabilities / Gaps**:
  - AWS Sentinel COG bucket endpoints occasionally experience AWS S3 egress or requester-pays changes.
  - Bounding box is hardcoded to a 3.2km window (`x - 1600, y + 1600`) around coordinates rather than dynamic user-supplied boundary polygon clipping.
  - Sentinel-2 has no thermal band, correctly documented as having `lst: None`.

### 3.3 MODIS, WorldCover, and SRTM
- **Implementation Location**: `backend/app/services/satellite.py:419-523` (`supplementary_earth_engine`).
- **Data Products**:
  - `MODIS/061/MOD11A2`: 1km 8-day Land Surface Temperature with `QC_Day` bitmasking (mandatory QA good quality and error <= 2K). Scaled by 0.02 - 273.15 -> °C.
  - `ESA/WorldCover/v200`: 10m global land cover classification (11 classes).
  - `USGS/SRTMGL1_003`: 30m global digital elevation model.
- **Vulnerabilities / Gaps**:
  - Dependent solely on Google Earth Engine.
  - Centre-point sampling rather than polygonal areal aggregation.

### 3.4 Target City Evaluation Rationale
- **Primary City: Ahmedabad** (23.0225° N, 72.5714° E)
  - **Relevance**: Pioneer of the Ahmedabad Heat Action Plan (HAP 2013), South Asia's first municipal heat resilience framework.
  - **EO Quality**: Semi-arid climate provides exceptionally clear, cloud-free imagery during peak heat season (March to May).
  - **Station Ground Truth**: 10+ CPCB/GPCB CAAQMS air quality stations (Maninagar, Chandkheda, Pirana, Rakhiyal, Bopal), CGWB groundwater observation wells, and AMC municipal ward boundaries.
- **Secondary City: Delhi** (28.6139° N, 77.2090° E)
  - Dense air quality station network (40+ CAAQMS), high heatwave frequency, but higher winter haze and monsoon cloud cover.
- **Secondary City: Hyderabad** (17.3850° N, 78.4867° E)
  - Deccan plateau terrain, rapid urbanization corridor, ~15 CAAQMS stations.

---

## 4. Deep Dive: Live Environmental Observation Ingestion

### 4.1 Weather: Open-Meteo & NASA POWER
- **Implementation Location**: `backend/app/services/sources.py:63-94` (`weather`), `sources.py:123-157` (`nasa_power`), `sources.py:160-234` (`weather_series`).
- **Capabilities**:
  - Calls `api.open-meteo.com/v1/forecast` for current readings and 3-day forecasts (variables: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `shortwave_radiation`, `soil_moisture_0_to_1cm`).
  - Calls `archive-api.open-meteo.com/v1/archive` with `models="era5_land"` for historical ranges.
  - NASA POWER point daily meteorology provides long-term solar radiation, precipitation, and air temperature.
  - `weather_series` aggregates hourly points into daily average temperature and relative humidity for frontend Recharts time-series visualization.
- **Conceptual Clarity**:
  - Provenance marks weather as `kind="modelled"` and `status="forecast"` or `"latest_available"`.
  - Explanatory notes clarify that weather model grid cells represent point air temperature at 2m above ground level, NOT Land Surface Temperature (LST).

### 4.2 Air Quality: OpenAQ v3 & CPCB
- **Implementation Location**: `backend/app/services/sources.py:303-343` (`air_quality`).
- **Current Behavior**:
  - Requires `OPENAQ_API_KEY` header.
  - Queries `https://api.openaq.org/v3/locations` (25 km radius, up to 8 locations).
  - For top 5 locations, calls `https://api.openaq.org/v3/locations/{id}/latest`.
- **Identified Defects & Gaps**:
  1. **Station Distance Omitted**: The API response dumps raw location coordinates but never computes the geodesic distance (km) from the target coordinates to each monitoring station.
  2. **Pollutant Parameters Unparsed**: Does not parse PM2.5, PM10, NO2, SO2, O3, CO concentrations, units, or timestamps into clean structured records.
  3. **Schema Incompatibility with `evidence.py`**:
     - `evidence.py:228` checks: `if asset["category"] in {"air_quality", "groundwater"} and isinstance(payload.get("stations"), list):`
     - `sources.air_quality()` returns: `{"locations": ..., "latest": ...}` without a top-level `"stations"` key.
     - Result: Live air quality assets can never be rendered on the map!
  4. **CPCB Absence**: No direct CPCB API or fallback station catalog for Indian cities.
  5. **Credential Error**: Missing `OPENAQ_API_KEY` raises `ValueError`, producing HTTP 422 instead of graceful `status="unavailable"` with clear setup guidance.

### 4.3 Groundwater: CGWB & India-WRIS
- **Implementation Location**: **Currently Absent**.
- **Existing Traces**:
  - `app/db.py:31`: Listed in `_ACQUISITION_KINDS = {"weather", "osm", "satellite", "monitoring", "groundwater"}`.
  - `app/services/evidence.py:28`: Defined in `LAYER_SPECS` as `"groundwater"` ("Groundwater monitoring stations", `depth_below_ground_m`, `observed`, `m below ground`).
  - `app/services/evidence.py:236-239`: Map layer logic expects `station.get("depth_below_ground_m")`.
- **Gaps to Implement**:
  - No function in `sources.py` exists to fetch or ingest CGWB (Central Ground Water Board) or India-WRIS data.
  - `AreaRequest.source` in `schemas.py` does not include `groundwater` as a valid source literal.
  - Need a dedicated adapter fetching depth-to-water level (mbgl), seasonal pre/post-monsoon water table fluctuations, observation dates, well coordinates, and distance to city center.
  - Explicit documentation must maintain clear physical distinction between:
    - *Groundwater Table Depth* (meters below ground level, phreatic aquifer storage).
    - *Surface Water* (water bodies, lakes, rivers via NDWI and OSM).
    - *Soil Moisture* (volumetric water content in the top 0-7 cm root zone from ERA5-Land).

---

## 5. Deep Dive: Backend Architecture & Test Suite Analysis

### 5.1 Architecture Overview
- **Entry Point**: `backend/app/main.py` (175 lines).
- **APIRouters (9 modules)**:
  - `routes/heat.py`: `/api/cities`, `/api/overview`, `/api/heat/map`, `/api/heat/hotspots`, `/api/heat/predict`.
  - `routes/models.py`: `/api/models`, `/api/models/train`, `/api/xai/explain`, `/api/xai/importance`, `/api/xai/shap`.
  - `routes/simulation.py`: `/api/interventions`, `/api/simulation/run`, `/api/simulation/results`.
  - `routes/optimization.py`: `/api/optimization/run`, `/api/optimization/results`.
  - `routes/risk.py`: `/api/risk/analyze`.
  - `routes/data.py`: `/api/data/assets`, `/api/data/layers`, `/api/data/status`, `/api/data/records`, `/api/data/series`, `/api/data/ingest`.
  - `routes/ai.py`: `/api/ai/chat`.
  - `routes/reports.py`: `/api/reports/generate`, `/api/reports/{id}/download`, `/api/reports/{id}/csv`, `/api/reports/{id}/markdown`.
  - `routes/workspace.py`: `/api/workspace`.
- **State Store**: `backend/app/services/state.py` decouples demo state (`DEMO_STATE`) from real-world evidence state (`REAL_STATE`) using a thread-safe recursive lock (`LOCK = threading.RLock()`).
- **Database Architecture**: `backend/app/db.py` uses SQLAlchemy 2.0 with PostgreSQL/PostGIS support (`Geometry("POLYGON", srid=4326)`) and SQLite local fallback. Four core tables:
  - `analysis_records`: JSON storage for raw payloads.
  - `zones`: Spatial polygon table with geometry column.
  - `data_assets`: Normalized evidence index with provenance metadata.
  - `schema_migrations`: Schema version control tracking applied migrations.
- **Security & Middleware**:
  - CORS middleware supporting configurable origins via `CORS_ORIGINS`.
  - In-memory rate limiting (180 requests/min per IP).
  - API Token header authentication (`Authorization: Bearer <API_TOKEN>`).
  - Path normalizer rewriting accidental double-prefix (`/api/api/` -> `/api/`).
  - HTTP security headers: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

### 5.2 Test Suite Audit (Pytest 9.2.0, Python 3.14 on Windows)
- Total tests executed: **365 tests**.
- Results: **251 passed, 97 failed, 17 errors, 15 warnings**.
- **Passing Suites (100% Pass)**:
  - `test_satellite.py`: 24 / 24 passed (GEE Landsat QA masks, thermal scaling, Sentinel COG WarpedVRT windowing, SCL masking, MODIS QC filtering, SUHII calculation).
  - `test_sources.py`: 34 / 34 passed (Open-Meteo, NASA POWER, OSM Overpass failover, WorldPop STAC, OpenAQ v3 resilience, Copernicus, GHSL).
  - `test_demographics.py`: 31 / 31 passed.
  - `test_ml_xai.py`: 39 / 39 passed.
  - `test_evidence_api.py`: 4 / 4 passed.
  - `test_analytical_mode.py`: 2 / 2 passed.
  - `test_foundation.py` & `test_phase1_foundations.py`: 7 / 7 passed.

### 5.3 Root Cause Analysis of Failures and Errors
1. **Root Cause 1: Strict Normal Mode 409 vs Legacy Test Expectation (97 Failures)**:
   - In `app/services/state.py:23-28`:
     ```python
     def resolve_mode(mode: str | None = None) -> str:
         return "demo" if mode == "demo" else "normal"
     ```
   - Notice: It completely ignores the `HEATWISE_DEMO_MODE=1` environment variable!
   - In `state(city, mode)`: When `mode is None` (as requested by all legacy test suites like `test_backend_m6_architecture.py`, `test_api.py`, `test_e2e_tiers.py`), it resolves to `"normal"`. In normal mode, without an `analysis_ready = True` real dataset, `state()` immediately raises `HTTPException(409, "No validated analytical model is active for this city...")`.
   - Fixing `resolve_mode()` to inspect `os.getenv("HEATWISE_DEMO_MODE")` or `os.getenv("HEATWISE_MODE")` when `mode is None` will immediately restore compatibility for legacy tests without compromising the request-scoped safety of production normal mode.
2. **Root Cause 2: OR-Tools CP-SAT Windows Access Violation Crash (17 Errors)**:
   - In `test_optimization.py`: Calling `cp_model.CpSolver().Solve()` triggers a Windows fatal exception (access violation in native C++ DLL) under Python 3.14.
   - Requires a safe execution guard or fallback solver wrapper in `optimization.py` to prevent native segfault crashes on Windows platforms during test runs.
3. **Root Cause 3: Analysis-Ready Promotion Gap**:
   - In `routes/data.py:153`: `metadata["analysis_ready"] = False` is hardcoded for every ingested source.
   - In `state.py:31-45`: `real_dataset_ready()` requires `metadata["analysis_ready"] is True`, `synthetic is False`, and complete properties (`lst`, `rural_reference`) for every zone feature.
   - Because no service promotes or fuses raw evidence into an analysis-ready dataset, normal analytical mode can never transition to ready.

---

## 6. Actionable Gap Analysis & Specification for Agents 1 & 6

### 6.1 Action Items for AGENT 1 (Satellite Data & Earth Observation Engineer)
Primary files: `backend/app/services/sources.py`, `backend/app/services/satellite.py`, `backend/app/services/geospatial.py`, related ingestion tests.

1. **Direct Landsat 8/9 STAC/COG Reader (Non-GEE Fallback)**:
   - Implement direct Landsat Collection 2 L2 ingestion using Element 84 / Microsoft Planetary Computer / AWS USGS Landsat STAC API and `rasterio` + `WarpedVRT`.
   - Enables real Landsat surface temperature ingestion even when Google Earth Engine credentials are not configured.
2. **Analytical Zonal Statistics Engine**:
   - Implement `calculate_zonal_statistics(raster_array, transform, crs, zone_geometries)` in `geospatial.py`.
   - Calculate zonal mean, median, min, max, standard deviation for LST, NDVI, NDWI, NDBI across analytical zones (municipal administrative wards).
   - Ingest genuine administrative ward boundary GeoJSON for Ahmedabad (48 wards across 6 zones).
3. **OpenAQ API v3 Parsing & Distance Computation**:
   - Update `sources.air_quality(lat, lon)`:
     - Compute Haversine distance ($d$ in km) from query coordinates to each monitoring station.
     - Parse individual pollutant parameters (PM2.5, PM10, NO2, SO2, O3, CO) into structured measurements with timestamps, values, and units.
     - Structure output to include top-level `"stations"` array matching the contract expected by `evidence.py:228-245`.
4. **CPCB (Central Pollution Control Board) Station Integration**:
   - Add CPCB Indian air quality station catalog for target cities (Ahmedabad, Delhi, Hyderabad) with CAAQMS live feed / fallback mapping.
5. **CGWB / India-WRIS Groundwater Adapter**:
   - Create `sources.groundwater(lat, lon, city)` in `sources.py`.
   - Ingest Central Ground Water Board monitoring well data: depth to water level (meters below ground level - mbgl), pre-monsoon vs post-monsoon trends, well coordinates, distance to city center, observation date.
   - Return structured `"stations"` array compatible with `evidence.py` groundwater layer mapping.
6. **Graceful Credential-Missing Degradation (Zero Synthetic Masquerading)**:
   - Replace `synthetic_satellite_fallback()` mock numbers with clean degraded responses:
     `{"status": "unavailable", "reason": "Earth Engine / OpenAQ credentials unconfigured", "setup_instructions": "..."}`.
   - Ensure external API failures never silently inject fabricated measurements.
7. **Real-Data Analysis Promotion Bridge**:
   - Build a dataset aggregation service that takes validated acquired evidence (Landsat LST, Sentinel indices, weather, air quality, groundwater) and compiles an analysis-ready GeoJSON FeatureCollection with `metadata["analysis_ready"] = True`, `metadata["synthetic"] = False`.

---

### 6.2 Action Items for AGENT 6 (Backend Architecture, API & Database Engineer)
Primary files: `backend/app/main.py`, `backend/app/routes/*`, `backend/app/services/state.py`, `backend/app/db.py`, `backend/app/schemas/*`, backend integration tests.

1. **State Mode Resolution Alignment (`app/services/state.py`)**:
   - Update `resolve_mode(mode: str | None = None)`:
     ```python
     def resolve_mode(mode: str | None = None) -> str:
         if mode in ("demo", "normal"):
             return mode
         env_mode = os.getenv("HEATWISE_DEMO_MODE") or os.getenv("HEATWISE_MODE")
         if env_mode in ("1", "true", "demo"):
             return "demo"
         return "normal"
     ```
   - This resolves the 97 test failures immediately while preserving explicit request-scoped mode overrides in production.
2. **AreaRequest & Routes Schema Parity**:
   - Add `"groundwater"` to `AreaRequest.source` literal in `backend/app/schemas.py`.
   - Add groundwater route handler in `backend/app/routes/data.py:ingest`.
   - Unify schema layout between `schemas.py` and `schemas/` directory to eliminate the `__path__` workaround.
3. **Structured Logging**:
   - Implement unified structured logging across `main.py` and services with timestamp, log level, request correlation ID, and logger name.
4. **Graceful External Credential Exception Handling**:
   - Update `main.py` exception handlers: Differentiate genuine user input errors (422) from unconfigured external API credentials, returning informative status and setup guidance.
5. **Database PostGIS & Migration Hardening**:
   - Verify PostGIS spatial index creation (`GIST(boundary)`) on PostgreSQL in `app/migrations.py`.
   - Expand `/api/health` to report connection pool health and PostGIS extension status.
6. **OR-Tools CP-SAT Solver Windows Compatibility Guard**:
   - Add a protected execution wrapper around `cp_model.CpSolver().Solve()` in `app/services/optimization.py` with error trapping or fallback heuristic to prevent Windows Python 3.14 access violation crashes.
7. **Test Suite Stabilization**:
   - Verify that all 365 tests pass cleanly with 0 failures and 0 errors across both normal and demo modes.

---

## 7. Evidence Reference Matrix

| Feature / Defect | Source File | Line Numbers | Observed Code / Evidence | Impact / Action Required |
|---|---|---|---|---|
| GEE Landsat Ingestion | `satellite.py` | 160-245 | `ee_mod.ImageCollection("LANDSAT/LC08/C02/T1_L2")`, QA_PIXEL bitmask 63 | Operational via GEE; needs non-GEE STAC fallback |
| GEE Synthetic Fallback | `satellite.py` | 528-586 | `synthetic_satellite_fallback()` returns mock floats | Violates no-synthetic rule; replace with no-data status |
| Sentinel S3 COG WarpedVRT | `satellite.py` | 286-370 | `rasterio.vrt.WarpedVRT` reading AWS S3 COGs at 100m EPSG:6933 | Operational direct raster reading |
| Zonal Statistics Engine | `geospatial.py` | 1-412 | Entire module lacks zonal mean/median aggregation function | Agent 1 must implement `calculate_zonal_statistics` |
| OpenAQ Missing Distance | `sources.py` | 303-343 | Calls `/locations` & `/latest`; no distance calculation | Agent 1 must calculate Haversine distance to station |
| OpenAQ Layer Incompatibility | `evidence.py` | 228-245 | Expects `payload.get("stations")`; `sources.py` returns `{"locations", "latest"}` | Format mismatch; Agent 1 must return `"stations"` |
| Groundwater Missing Adapter | `sources.py` | 1-419 | Zero mention or implementation of CGWB / India-WRIS | Agent 1 must implement `sources.groundwater()` |
| Analysis Ready Hardcoded False | `routes/data.py` | 153 | `metadata["analysis_ready"] = False` | Blocks normal mode; Agent 1/6 must build promotion bridge |
| Mode Resolution Bug | `state.py` | 23-28 | `resolve_mode()` ignores `HEATWISE_DEMO_MODE=1` | Causes 97 test failures; Agent 6 must check env var |
| OR-Tools Access Violation | `optimization.py` | 256 | `solver.Solve(model)` crashes with access violation on Win32 Python 3.14 | Causes 17 test errors; Agent 6 must add safety guard |
