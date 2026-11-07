# Verification record — 7 November 2026

## Executed successfully

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
