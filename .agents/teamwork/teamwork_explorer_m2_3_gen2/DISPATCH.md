## 2026-11-08T22:43:41Z
[Message] timestamp=2026-11-08T22:43:41Z sender=34ff78fc-de7b-4a98-abfc-54d6c3495098 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer M2-3 (Gen 2): Adapter Unit Test Expansion Specialist for Milestone 2.

Your predecessor wrote an extensive 188-line analysis before being interrupted by a transient network error.
READ PREDECESSOR ANALYSIS FIRST:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3\analysis.md

MANDATORY CONTEXT:
Read ORIGINAL_REQUEST.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md

YOUR MISSION:
Your predecessor already completed the thorough audit of all 11 adapters in `backend/app/services/sources.py` and the offline mock architecture.
Your specific task is to finalize the complete, production-grade drop-in blueprint for `backend/tests/test_sources.py`:
1. Preserve all 5 existing tests in `backend/tests/test_sources.py`.
2. Add comprehensive offline mock tests for the 6 missing adapters:
   - Open-Meteo Weather (`weather()`) both ERA5-Land reanalysis and 3-day forecast modes.
   - OpenAQ v3 Air Quality (`air_quality()`) including station fault tolerance (when 1 station fails, logs to `latest_unavailable_location_ids` without failing the batch).
   - WorldPop STAC (`worldpop()`) catalog discovery and country/year filtering.
   - GHSL STAC (`ghsl_catalog()`) tile resolution, bbox, and empty tile fallback.
   - Sentinel-2 COG WarpedVRT (`sentinel_indices()`) with mock rasterio/VRT, SCL cloud masking, NDVI/NDWI/NDBI computation, all-cloud edge case, and SSRF domain protection.
   - Google Earth Engine (`earth_engine()` & `supplementary_earth_engine()`) with mock `ee` chaining, Landsat LST, MODIS, SRTM, Sentinel-2, and database serialization safety.
3. Test OSM Overpass mirror failover resilience: primary fails -> secondary succeeds; both fail -> HTTP 502.
4. Ensure test isolation with `sources._CACHE.clear()`.
5. Ensure 100% offline determinism (0 network calls, 0 credentials needed, execution time <2s).

OUTPUT REQUIREMENTS:
- Working directory: d:\Urban-Heat-Resilience-AI
- State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3_gen2
- Maintain progress.md with timestamps.
- Write your complete drop-in blueprint and rationale into `analysis.md`.
- Write your final handoff into `handoff.md` following the 5-component protocol: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
- Send a completion message via send_message to the orchestrator (conversation ID: 34ff78fc-de7b-4a98-abfc-54d6c3495098).
- Do NOT edit production code directly (you are read-only).
