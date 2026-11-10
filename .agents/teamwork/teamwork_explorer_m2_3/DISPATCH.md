## 2026-11-08T22:06:30Z
From: 34ff78fc-de7b-4a98-abfc-54d6c3495098 (Orchestrator)
Message:
You are Explorer M2-3: Adapter Unit Test Expansion & Test Resilience Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read previous survey findings:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_data_tests\survey_data_tests.md

Your mission for Milestone 2:
1. Examine all 11 external data source adapters in `backend/app/services/sources.py`.
2. Address the testing blind spots identified in Survey 3:
   - 6 adapters lack unit tests:
     1. Open-Meteo Weather (`weather()`)
     2. OpenAQ v3 (`air_quality()`)
     3. WorldPop STAC (`worldpop()`)
     4. GHSL STAC (`ghsl_catalog()`)
     5. Sentinel-2 COG WarpedVRT (`sentinel_indices()`)
     6. Google Earth Engine (`earth_engine_data()`)
3. Design mock fixtures and comprehensive unit tests for `backend/tests/test_sources.py` (or a dedicated `backend/tests/test_adapters.py`) using `unittest.mock` / `pytest_mock` / `respx` / `httpx.MockTransport` so they run 100% offline without live network or external API keys.
4. Verify:
   - Response parsing for each provider.
   - Dual-mirror failover (OSM Overpass).
   - Strict provenance rule: HTTP 502 Bad Gateway is returned on upstream failure; synthetic fallback data is NEVER masqueraded as real live data.
   - Boundary coordinates, date ranges, and empty result handling.
5. Provide complete drop-in blueprints in `analysis.md` and `handoff.md`.
6. Send completion message to orchestrator. Do not modify source code.
