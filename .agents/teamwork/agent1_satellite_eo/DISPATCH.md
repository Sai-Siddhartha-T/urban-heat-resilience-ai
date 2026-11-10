## 2026-11-10T12:29:01Z
You are specialized AGENT 1: Satellite Data and Earth Observation Engineer working on Milestone M1 (Earth Observation & Real Environmental Ingestion) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent1_satellite_eo
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_2\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_2\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_2\handoff.md` first.
Your exclusive file ownership:
- `backend/app/services/sources.py`
- `backend/app/services/satellite.py`
- `backend/app/services/geospatial.py`
- `backend/tests/test_satellite.py`
- `backend/tests/test_sources.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R2 & R3):
1. Landsat 8/9 STAC/COG Direct Ingestion:
   - Implement direct Landsat Collection 2 Level-2 Surface Temperature ingestion using STAC (Planetary Computer or AWS Landsat STAC) and `rasterio` + `WarpedVRT` when Google Earth Engine credentials are not present. Ensure USGS thermal scaling (`ST_B10 * 0.00341802 + 149.0 - 273.15`) and QA bitmasking are applied.
2. Zonal Statistics Engine:
   - In `backend/app/services/geospatial.py`, implement `calculate_zonal_statistics(raster_array, transform, crs, zone_geometries)` to aggregate raster pixels (mean, median, min, max, std) across analytical ward boundaries.
3. Eliminate Synthetic Fallback:
   - In `backend/app/services/satellite.py`, replace `synthetic_satellite_fallback()` mock numbers with clean degraded responses: `{"status": "unavailable", "reason": "Earth Engine / Satellite credentials unconfigured", "setup_instructions": "..."}`.
   - Zero synthetic or placeholder data may silently enter real-data results!
4. OpenAQ v3 Station Distance & Pollutant Parsing:
   - In `backend/app/services/sources.py:air_quality()`, calculate Haversine distance (km) to each monitoring station.
   - Parse individual pollutants (PM2.5, PM10, NO2, SO2, O3, CO) into structured measurements with timestamps.
   - Format output to include a top-level `"stations"` array matching the schema expected by `backend/app/services/evidence.py:228-245`.
   - Add CPCB Indian air quality station catalog for target cities (Ahmedabad, Delhi, Hyderabad).
5. CGWB / India-WRIS Groundwater Adapter:
   - In `backend/app/services/sources.py`, implement `groundwater(lat: float, lon: float, city: str)`:
     - Ingest Central Ground Water Board monitoring well data: depth to water level (meters below ground level - mbgl), pre/post-monsoon trends, coordinates, distance (km), observation dates.
     - Return structured `"stations"` array compatible with `evidence.py` groundwater layer.
     - Maintain clear distinction between groundwater depth (mbgl), surface water, and soil moisture.
6. Real-Data Analysis Promotion Bridge:
   - Implement a function that compiles acquired live evidence into an analysis-ready zone FeatureCollection with `metadata["analysis_ready"] = True`, `metadata["synthetic"] = False`.
7. Verification:
   - Run `pytest backend/tests/test_satellite.py backend/tests/test_sources.py` (ensure all tests pass).
   - Document all changes and test results in `handoff.md`.
