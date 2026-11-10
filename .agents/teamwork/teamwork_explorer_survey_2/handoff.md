# Handoff Report: Survey 2 — Earth Observation, Environmental Ingestion & Backend Architecture

**Agent**: `teamwork_explorer` (Survey 2)  
**Recipient**: Lead Orchestrator (`ef9393af-13d2-4069-906d-ff502c4a45d2`)  
**Scope**: Requirements R2 (Earth Observation), R3 (Live Environmental Ingestion), R7 (Backend Architecture)  
**Primary Downstream Assignees**: Agent 1 (Satellite Data & Earth Observation Engineer), Agent 6 (Backend Architecture, API & Database Engineer)  
**Date**: 2026-11-10  

---

## 1. Observation

1. **Satellite Ingestion & GEE Dependency (`backend/app/services/satellite.py`)**:
   - `earth_engine()` at `satellite.py:160-245` correctly queries `LANDSAT/LC08/C02/T1_L2` and `LANDSAT/LC09/C02/T1_L2`, applies QA_PIXEL bitmask (bits 0..5, value 63), QA_RADSAT saturation filter (== 0), and converts ST_B10 to Celsius (`ST_B10 * 0.00341802 + 149.0 - 273.15`).
   - At `satellite.py:596, 623, 683`, when Earth Engine is unconfigured or fails, `fetch_landsat8()` calls `synthetic_satellite_fallback("landsat8")` which returns hardcoded mock floats (`"ndvi": 0.45, "ndwi": -0.15, "ndbi": 0.12, "lst": 33.5`) with `"synthetic": True`.
   - Sentinel-2 has a direct open COG reader via Element 84 Earth Search STAC and AWS S3 in `satellite.py:286-370` (`sentinel_indices`) using `rasterio` and `WarpedVRT` at 100m EPSG:6933, but **no equivalent direct STAC/COG reader exists for Landsat**.
   - `geospatial.py:1-412` contains raster reproject, clipping, cloud masking, and spectral indices, but **lacks a zonal statistics engine** to aggregate raster pixels across analytical zone/ward polygons.

2. **Environmental Observation Ingestion (`backend/app/services/sources.py`)**:
   - Open-Meteo weather is implemented in `sources.py:63-94` (`weather`) and `sources.py:160-234` (`weather_series`), properly tagged with `kind="modelled"` and timestamps.
   - OpenAQ v3 in `sources.py:303-343` queries `/locations` and `/latest`. However:
     - Geodesic distance to monitoring station is never calculated.
     - Individual pollutants (PM2.5, PM10, NO2, SO2, O3, CO) are not parsed or normalized.
     - Output payload returns `{"locations": locations, "latest": latest}` without a `"stations"` array, but `evidence.py:228` explicitly checks `if asset["category"] in {"air_quality", "groundwater"} and isinstance(payload.get("stations"), list)`. Consequently, OpenAQ data cannot be rendered as a map layer.
     - Unconfigured `OPENAQ_API_KEY` raises `ValueError`, resulting in HTTP 422 instead of graceful no-data status.
     - CPCB direct API / CAAQMS network is not implemented.
   - Groundwater (CGWB / India-WRIS): **Completely absent from `sources.py`**. There is zero implementation of a groundwater adapter, and `AreaRequest.source` in `schemas.py` omits `groundwater`.

3. **Analysis Readiness & State Management (`backend/app/routes/data.py`, `backend/app/services/state.py`)**:
   - At `routes/data.py:153`: `metadata["analysis_ready"] = False` is hardcoded for every ingested live asset.
   - At `state.py:31-45`: `real_dataset_ready()` requires `metadata["analysis_ready"] is True`, `synthetic is False`, and measured labels (`lst`, `rural_reference`) on every feature. No promotion/fusion bridge exists, leaving normal mode permanently unable to train or analyze (HTTP 409).
   - At `state.py:23-28`: `resolve_mode()` is implemented as `return "demo" if mode == "demo" else "normal"`, completely ignoring the `HEATWISE_DEMO_MODE=1` environment variable.

4. **Test Suite Status (`pytest` execution)**:
   - Tool command: `pytest` (across 20 test files, 365 collected items).
   - Result: **251 passed, 97 failed, 17 errors, 15 warnings in 106s**.
   - `test_satellite.py` (24/24) and `test_sources.py` (34/34) pass 100%.
   - The 97 failures are caused by `resolve_mode()` returning `"normal"` when `mode is None`, resulting in HTTP 409 ("No validated analytical model is active for this city") in legacy tests expecting demo data.
   - The 17 errors are caused by an access violation in OR-Tools native C++ solver binary (`solver.Solve(model)`) under Python 3.14 on Windows in `test_optimization.py`.

---

## 2. Logic Chain

1. **From Observation 1 to Landsat Non-GEE Fallback**:
   - Observation 1 shows that Landsat ingestion relies exclusively on `_ensure_ee_initialized()` in `satellite.py:160`, whereas Sentinel-2 has both GEE and Element 84 COG reader (`sentinel_indices`).
   - If Earth Engine credentials are absent, `fetch_landsat8()` calls `synthetic_satellite_fallback()`, returning synthetic numbers.
   - Requirement R2 mandates: *"Replace synthetic satellite and environmental inputs with an actual data acquisition and preprocessing pipeline... do not silently replace failed satellite acquisitions with synthetic data."*
   - Therefore, a direct open STAC/COG reader for Landsat Collection 2 L2 (via AWS / Planetary Computer) must be added, and unconfigured credentials must degrade to a clean `unavailable` status with setup instructions rather than returning mock floats.

2. **From Observation 1 to Zonal Aggregation Requirement**:
   - Observation 1 shows that `satellite.py` only takes 500 point samples or an overall bounding box mean, while `geospatial.py` has no polygon zonal statistics function.
   - Requirement R2 mandates: *"Implement spatial clipping, cloud masking, spatial aggregation into analytical zones."*
   - Therefore, Agent 1 must implement a zonal statistics function in `geospatial.py` that computes zonal mean, median, min, max for LST, NDVI, NDWI, NDBI across municipal ward polygons (such as Ahmedabad AMC's 48 wards).

3. **From Observation 2 to Air Quality Layer Fix & Groundwater Adapter**:
   - Observation 2 reveals that `sources.air_quality()` does not compute station distance, does not parse pollutant parameters, and returns `{"locations": ..., "latest": ...}` instead of `{"stations": [...]}`.
   - In `evidence.py:228-245`, map layers for air quality strictly require `payload.get("stations")` with `latitude`, `longitude`, and `measurements`.
   - Because `stations` is missing, acquired air quality data can never be rendered on the map.
   - Additionally, Observation 2 confirms that CGWB / India-WRIS groundwater ingestion is completely missing from `sources.py`.
   - Therefore, Agent 1 must:
     a) Update `sources.air_quality()` to compute Haversine distance, parse pollutants (PM2.5, PM10, etc.), and output the `"stations"` array.
     b) Implement a new `sources.groundwater()` adapter for CGWB / India-WRIS data.
     c) Agent 6 must add `"groundwater"` to `AreaRequest.source` in `schemas.py` and `routes/data.py`.

4. **From Observation 3 to Analysis-Ready Dataset Promotion Bridge**:
   - Observation 3 shows that all live ingested assets have `analysis_ready = False` (`routes/data.py:153`).
   - Normal analytical mode requires `real_dataset_ready()` (`state.py:31-45`), which checks `analysis_ready is True`.
   - Without an explicit fusion pipeline to combine acquired satellite, weather, and air quality assets into an analysis-ready zone FeatureCollection, normal analytical mode can never operate.
   - Therefore, Agent 1 and Agent 6 must implement a real dataset compilation/promotion service that fuses acquired evidence into an analysis-ready dataset.

5. **From Observation 4 to Test Suite Resolution**:
   - Observation 4 shows that 97 test failures stem directly from `resolve_mode()` in `state.py` ignoring `HEATWISE_DEMO_MODE=1`.
   - When legacy tests call endpoints like `/api/overview?city=Ahmedabad` without `mode="demo"`, `resolve_mode()` evaluates to `"normal"`, raising HTTP 409.
   - Checking `os.getenv("HEATWISE_DEMO_MODE")` in `resolve_mode()` when `mode is None` will immediately restore backwards compatibility for tests while preserving strict request-scoped mode overrides in production.
   - Observation 4 also shows 17 errors due to an OR-Tools CP-SAT Windows Python 3.14 native crash. Adding a protected execution guard/fallback will stabilize the test suite.

---

## 3. Caveats

1. **External API Network Availability**: Open-Meteo, OpenAQ, Element 84 STAC, and Copernicus endpoints require outbound internet access. In sandboxed or offline environments, mocked adapter tests (`test_sources.py`) verify logic, but live fetches require network egress.
2. **Third-Party Credentials**: Google Earth Engine requires GCP credentials; OpenAQ requires an API key for high-volume endpoints. The platform design must support fully functional operation with graceful no-data indicators when credentials are not configured.
3. **Python 3.14 C-Extension Stability**: Pre-release Python 3.14 on Windows exhibits occasional binary instability with certain heavy C++ packages (like OR-Tools native CP-SAT solver). Test runners should account for this platform-specific edge case.

---

## 4. Conclusion

The Heatwise backend has strong architectural foundations: modular FastAPI APIRouters, dual PostgreSQL/PostGIS and SQLite support, strict Pydantic validation, and complete test suites for satellite and sources (58/58 passing).

However, to satisfy requirements **R2**, **R3**, and **R7**, the following concrete implementations must be delegated:

### For Agent 1 (Satellite Data & Earth Observation Engineer):
1. **Direct Landsat 8/9 STAC/COG Reader**: Non-GEE raster ingestion via AWS / Planetary Computer using `rasterio` + `WarpedVRT`.
2. **Analytical Zonal Statistics Engine**: Add `calculate_zonal_statistics()` in `geospatial.py` to aggregate raster pixels into ward polygons. Ingest Ahmedabad AMC ward boundaries GeoJSON.
3. **OpenAQ Distance & Formatting Fix**: Calculate Haversine station distance, parse individual pollutants, and format output as `"stations"` array matching `evidence.py`.
4. **CPCB Station Integration**: Ingest CPCB CAAQMS stations for target cities.
5. **CGWB / India-WRIS Groundwater Adapter**: Implement `sources.groundwater()` with station depth (mbgl), trends, and distance.
6. **Eliminate Synthetic Fallback**: Replace mock numbers in `synthetic_satellite_fallback()` with clean `unavailable` status and setup documentation.
7. **Analysis-Ready Fusion Bridge**: Build service compiling acquired evidence into an `analysis_ready = True` real FeatureCollection.

### For Agent 6 (Backend Architecture, API & Database Engineer):
1. **Mode Resolution Alignment**: Fix `resolve_mode()` in `state.py` to check `HEATWISE_DEMO_MODE` env var when `mode is None` (clears 97 test failures).
2. **Schema & Endpoint Parity**: Add `"groundwater"` to `AreaRequest.source` and connect in `routes/data.py`. Clean up `schemas.py` / `schemas/` directory duality.
3. **Structured Logging**: Add unified structured JSON logging across `main.py` and services.
4. **Graceful Credential Exception Handling**: Return structured unavailable status instead of HTTP 422 for unconfigured external services.
5. **OR-Tools Solver Guard**: Implement protected execution wrapper around CP-SAT solver to prevent Windows native crashes.
6. **Full Test Stabilization**: Ensure 100% of the 365 tests pass cleanly.

---

## 5. Verification Method

To independently verify all findings and test subsequent implementations:

1. **Verify Current Ingestion Tests (Satellite & Sources)**:
   ```powershell
   pytest backend/tests/test_satellite.py backend/tests/test_sources.py
   ```
   *Expected outcome*: 58 passed in ~23s.

2. **Verify Mode Resolution & Architecture Tests**:
   ```powershell
   pytest backend/tests/test_backend_m6_architecture.py backend/tests/test_analytical_mode.py backend/tests/test_evidence_api.py
   ```
   *Current state*: 18 passed, 3 failed (409 Conflict due to `resolve_mode` bug).

3. **Verify Full Test Suite**:
   ```powershell
   pytest
   ```
   *Current state*: 251 passed, 97 failed, 17 errors in ~106s.  
   *Target after Agent 1 and Agent 6 fixes*: 365 passed, 0 failed, 0 errors.

4. **Verify Application Import and Startup**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'backend'); from app.main import app; print(app.title)"
   ```
   *Expected output*: `Heatwise · Urban Heat Intelligence`.
