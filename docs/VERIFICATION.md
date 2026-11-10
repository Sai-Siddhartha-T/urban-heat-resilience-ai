# Verification record — 9 November 2026

## Executed successfully

- **175 backend tests passed (100%)**: Full automated pytest suite (`pytest backend/tests/ -v`) passed completely in ~51.86s.
  - `backend/tests/test_foundation.py` (3 tests): Health check, synthetic provenance & geometry, spectral indices & cloud mask.
  - `backend/tests/test_api.py` (5 tests): Integrated workflow, input errors, unconfigured provider fallback, API tokens, explicit upstream failures.
  - `backend/tests/test_pipeline.py` (5 tests): Three-model spatial evaluation, SHAP additivity, simulation constraints, optimizer feasibility/infeasibility, convenience inputs, multi-criteria risk index.
  - `backend/tests/test_ai.py` (1 test): Provider schema & model validation.
  - `backend/tests/test_sources.py` (34 tests): Ingestion adapters for Open-Meteo (forecast, ERA5 reanalysis), NASA POWER, OpenAQ v3, WorldPop, GHSL STAC, Sentinel-2 COG / WarpedVRT windowing, Copernicus, Google Earth Engine, OSM Overpass mirror failover, in-memory cache isolation.
  - `backend/tests/test_challenger_m2.py` (19 tests): Spatial clustering boundary stress tests, dynamic partition scaling for $N \in [60, 89]$ zones, collinear/concentric zones, AI measurement unit regexes, scientific notation parsing, zero-rounding leakage elimination.
  - `backend/tests/test_challenger_m2_api_budget.py` (30 tests): CP-SAT optimizer financial budget constraints (zero budget, infinite budget, tight budget, Pareto-frontier verification, CapEx/OpEx tracking).
  - `backend/tests/test_e2e_tiers.py` (78 tests): Comprehensive end-to-end testing across 4 tiers:
    - Tier 1: Feature Coverage (50 tests, 5 tests across each of 10 functional domains).
    - Tier 2: Boundary & Corner Cases (22 tests, coordinate limits, zero denominators, capacity limits).
    - Tier 3: Cross-Feature Pairwise Workflows (3 tests, Ingest -> Predict -> SHAP -> Risk -> Optimize -> AI Chat -> Export).
    - Tier 4: Real-World Scenarios (3 tests, Ahmedabad Heatwave Crisis, Rapid Urbanization Dual Hazard, Industrial Corridor Retrofit).

- **54 frontend Vitest tests passed (100%)**:
  - `frontend/src/tests/metrics.test.ts` (11 tests): Shared domain metrics, SUHII calculations, cooling potential, risk classification.
  - `frontend/src/tests/zoneCompare.test.ts` (6 tests): Multi-zone selection updates, delta metrics, disparity calculations.
  - `frontend/src/tests/weather.test.ts` (3 tests): Weather extremes computation, heat index approximation, diurnal swings.
  - `frontend/src/tests/integration_challenge.test.ts` (18 tests): Plural route mappings, deep linking, error typing (`ApiError`), request abort/cancellation.
  - `frontend/src/tests/button.test.tsx` (5 tests): Shadcn/Radix button variant rendering and click interactions.
  - `frontend/src/tests/api.test.ts` (11 tests): Strongly typed API service methods and error handling.

- **Frontend Production Build clean**:
  - `npm --prefix frontend run build` (`tsc -b && vite build`) transformed 2,105 modules and generated production bundle in ~19.97s with zero TypeScript compilation errors or warnings.

- **Backend Architecture & Startup**:
  - FastAPI modular routers in `backend/app/routes/` with clean separation of concerns and slim `main.py` (<100 lines).
  - Thread-safe state management in `backend/app/services/state.py`.
  - Lazy model loading & disk caching (`FAST_STARTUP=1`, `PREWARM_STATE=0`), reducing cold boot overhead.
  - Dynamic spatial partitioning (`max(1, min(15, n // 6))`) and KMeans 2D geographic clustering fallback.
  - AI guardrail regex refinement preventing backtracking on unit descriptions and ensuring numeric prose grounding.

- Inspected `/workspace` before implementation: no application or repository was present. Initialized `heatwise/` without replacing existing user code.
- Frontend: React/TypeScript production compilation and Vite build completed.
- FastAPI startup completed and `/api/health` returned `ok` with `PostgreSQL/PostGIS`.
- PostgreSQL container: `postgis/postgis:16-3.4-alpine`, healthy. PostGIS reported version 3.4. All 324 stored zone boundaries passed `ST_IsValid`.
- **16 backend tests passed**, with two dependency deprecation warnings (pytest/anyio and FastAPI TestClient/httpx). Tests now use isolated temporary SQLite databases and model directories. The same integration workflows had also passed against the development PostGIS instance before isolation was added.
- Backend coverage: seed provenance; geometry/index behavior; cloud masks; three-model spatial evaluation; SHAP additivity; risk vulnerability changes; simulation resource/compatibility/protection checks; optimizer feasibility/infeasibility; complete API workflow; malformed inputs; missing-provider fallback; token access; explicit upstream errors; provider model/schema/source validation; cloud-filtered satellite catalog and OSM geometry conversion.
- Chromium browser workflow: 324 interactive map cells; prediction and SHAP pages; risk recalculation; saved scenario; constrained optimizer; labeled local assistant fallback; report generation and CSV download; city switching; mobile menu; no horizontal overflow at 390px. **No JavaScript page errors** in this workflow.
- Desktop and mobile screenshots were visually inspected. A basemap returning an API-key watermark was discovered and replaced with actual OpenStreetMap tiles. Fixed tiles are fetched by the backend with an identifying User-Agent and cached; source attribution remains visible. Fonts are bundled locally under their OFL licenses.
- Open-Meteo current weather: live response retrieved.
- Open-Meteo ERA5-Land historical weather: 48 hourly timestamps retrieved for 1–2 May 2025.
- WorldPop India/2020: one real matching dataset catalog entry retrieved. No population raster or age/sex coverage claim is made.
- Sentinel-2 public catalog: four qualifying scene footprints retrieved for Ahmedabad, May 2025.
- Sentinel-2 COG processing: real red/NIR/green/SWIR/SCL data fetched; common EPSG:6933 100m grid; 1,024 valid pixels. Actual processed means: NDVI 0.5360573242, NDWI −0.4453951165, NDBI 0.0225884045. These are optical indices for one bounded scene window, not citywide LST or validated heat predictions.
- Docker Compose configuration validated. Full application image build was not run due the remaining disk constraint.

## Actual synthetic holdout evaluation

| Model | Validation RMSE °C | Test R² | Test RMSE °C | Test MAE °C |
|---|---:|---:|---:|---:|
| Random Forest | 0.587941 | 0.928722 | 0.511899 | 0.410495 |
| XGBoost | 0.501125 | 0.942477 | 0.459863 | 0.368391 |
| LightGBM | 0.497123 | 0.940034 | 0.469526 | 0.373430 |

LightGBM selected on validation only. Split: 162 train / 54 validation / 54 buffer / 54 test. Empirical validation-residual range ±0.899702°C. SHAP additivity passed to within 1e-4°C. These are genuine calculations on explicitly synthetic labels, not validation against satellite observations.

## Not live-verified / unavailable

- Groq and Gemini: no credentials or configured model IDs. Request construction, model-list checks, JSON validation and fallback were exercised using mocked transports. No successful live LLM generation is claimed.
- Earth Engine Landsat, Sentinel, MODIS, WorldCover and SRTM adapters: no project credentials. Code paths are implemented; credentialed remote execution remains unverified.
- Overpass: primary endpoint returned HTTP 406; alternate endpoint timed out. Geometry conversion was tested with an isolated mock. No successful live OSM feature ingestion is claimed.
- OpenAQ: key unavailable; station adapter unverified. Pollutant observations are not implemented.
- External real-labeled training CLI: implemented but no appropriate observed training dataset was supplied. The dashboard continues to use explicitly synthetic models.
- Full Docker app image, shared multi-user authentication, public hosting and real-world intervention calibration are not verified or delivered.

## Reproduction

See the root README for startup, testing, credentials and training commands. Test output, browser results, exact model evaluation JSON, processed live optical data and screenshots accompany the handoff. No `.env`, provider secrets, virtual environment, dependency cache or personal data is included in the source archive.
