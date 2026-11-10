## 2026-11-09T13:53:31Z
You are AGENT 1: Satellite Data and Earth Observation Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_satellite_m1\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Your exclusive write ownership:
- `backend/app/services/geospatial.py` (create)
- `backend/app/services/satellite.py` (create)
- `backend/app/services/sources.py` (satellite adapter modularization with backward-compatible re-exports)
- `backend/tests/test_sources.py` and/or `backend/tests/test_satellite.py`

Tasks:
1. Modularize satellite and remote sensing logic into `backend/app/services/satellite.py` and `backend/app/services/geospatial.py`, keeping clean re-exports in `backend/app/services/sources.py` so existing callers do not break.
2. Ingest real Landsat 8/9 Collection 2 Level-2 Surface Temperature (ST_B10) with QA_PIXEL (cloud/cirrus/shadow masking) and QA_RADSAT saturation filtering, converting USGS scaling factors to Celsius.
3. Ingest Sentinel-2 L2A optical imagery (both via Google Earth Engine harmonized median composite and Element 84 COG windowing via rasterio WarpedVRT to EPSG:6933 at 100m with SCL cloud/shadow filtering).
4. Integrate MODIS MOD11A2 8-day composite for regional LST observations.
5. Implement spectral indices: NDVI, NDWI, NDBI, and document NDBaI radiometric non-commensurability caveat.
6. Handle missing pixels and invalid geometries gracefully with rasterio / GeoPandas / shapely.
7. Calculate Surface Urban Heat Island Intensity: SUHII = Urban LST - Rural Reference LST, and document urban vs rural reference methodology.
8. Store acquisition dates, spatial resolution, sensor source, and processing metadata.
9. Maintain clearly labelled synthetic demonstration fallback with explicit provenance metadata when live satellite data is unavailable or unconfigured. Never silently substitute fabricated satellite observations.
10. Run tests (`pytest`) and verify all tests pass with 0 regressions.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_satellite_m1\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method with exact test execution commands and results.
When done, message the orchestrator.
