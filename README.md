# Urban Heat Resilience AI

## Heatwise — Urban Heat Intelligence

A functional full-stack research prototype: live geospatial ingestion, genuine spatial ML evaluation and TreeSHAP, risk screening, hypothetical intervention simulation, constraint-aware optimization, evidence-grounded assistant adapters, and an integrated nine-page dashboard.

**Default heat predictions, environmental features, population, and age data are synthetic.** Model metrics do not demonstrate real-world accuracy. Intervention coefficients are hypothetical. Surface temperature is not air temperature. See [METHODOLOGY.md](docs/METHODOLOGY.md) for all equations, coefficients, assumptions, quality masks and limitations.

## Start locally

### Prerequisites
- Python 3.12+ (ensure the `python` command points to Python 3.12 or later)
- Node 22+ and npm
- (Optional) Playwright for end‑to‑end browser smoke tests. Install with `pip install playwright && playwright install` if you have internet access.

### Backend
```bash
# Create virtual environment and install backend requirements
python -m venv .venv
.venv\Scripts\activate  # on Windows PowerShell
pip install -r backend/requirements.txt
```

### Frontend
```bash
npm --prefix frontend ci   # install dependencies (already done)
npm --prefix frontend run build   # production build
```

### Run the application
```bash
# Linux/macOS
cp .env.example .env
bash scripts/run-local.sh

# Windows PowerShell
Copy-Item .env.example .env
pwsh ./scripts/run-local.ps1
```

The API will be available at `http://127.0.0.1:8000` and the Vite dev server proxies `/api` to it.

If you prefer to run the backend directly:
```bash
cd backend
python -m app
```

### End‑to‑end smoke test (optional)
```bash
python scripts/browser_smoke.py   # runs a quick Playwright smoke test against the running server
```
If Playwright is not installed, the script will exit gracefully with a notice.

### Testing
```bash
# Backend tests
pytest -q

# Frontend Vitest suite
npm --prefix frontend test -- --run
```
All tests should pass.

For frontend development, keep FastAPI on 8000 and run `npm --prefix frontend run dev`. Vite proxies `/api` to FastAPI. React/TypeScript with Vite was selected from the requested Next.js/React options because FastAPI owns the API and serves the compiled frontend; no Node SSR is required.

## PostgreSQL / PostGIS

```bash
docker compose up -d db
# Set DATABASE_URL in .env:
# postgresql+psycopg://heatwise:heatwise@localhost:5433/heatwise
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The project uses `postgis/postgis:16-3.4-alpine`. The larger Debian image exceeded the development environment's disk capacity; Alpine started successfully. PostGIS 3.4 and all 324 WGS84 polygon geometries were verified. Local SQLite is an explicit fallback and does not offer PostGIS queries. Switching database URLs does not automatically migrate prior records.

The schema has a normalized `zones` table with PostGIS geometry, city and properties, plus typed `analysis_records` for datasets, weather, predictions/model evaluations, scenarios, optimization, conversations and generated reports. This deliberately compact prototype schema does not implement separate enterprise tables for every entity or multi-user ownership. Raster arrays/large source rasters are not stored as ordinary relational blobs; small bounded index grids and metadata are retained as JSON. Production-scale raster storage needs object storage.

## Docker application

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000. Docker binds the app and database to loopback; `.env` supplies provider configuration. The app runs as a non-root user and uses named volumes for DB, samples and models. Change the example DB password for any shared environment. Database-only Compose startup and configuration validation were executed; **the full application image build was not executed in the constrained development filesystem**.

For a TLS-inspecting build proxy, pass the trusted CA as BuildKit secret `proxy_ca`. No certificate verification is disabled. Example: `docker build --secret id=proxy_ca,src=/path/to/trusted-ca.pem -t heatwise .`. A production deployment also needs HTTPS, actual user authorization, operational monitoring, backups and a credential strategy. The optional `API_TOKEN` is a shared prototype API token, not a multi-user identity system. Set it in server environment and enter it in Workspace settings for the browser session. Public fixed basemap tile requests are exempt from that token. Static UI assets are public; API data requires the token when configured.

Sites hosting cannot execute Python/FastAPI/OR-Tools, so no nonfunctional static-only deployment was published. This is a local/container application, not a hosted production URL.

## Project structure

```text
heatwise/
  frontend/
    src/App.tsx                # Modular dashboard root orchestrator (<110 lines)
    src/pages/                 # 10 dedicated view pages (Overview, Map, Predictions, Explain, Risk, Simulator, Optimizer, Assistant, Reports, ZoneCompare)
    src/components/            # Modular components (layout, common, zone, charts, modals, BoundarySketch, HeatMap)
    src/services/              # Strongly-typed API client services (heat, ml, simulation, optimization, risk, weather, ai, reports)
    src/types/                 # Strict TypeScript domain interfaces (geojson, simulation, weather, optimization, chat, risk, ml)
    src/lib/                   # Shared domain utilities and constants
    src/tests/                 # Vitest component, utility, and API client test suite (54 tests)
    src/styles.css             # Responsive dashboard styling
    src/assets/                # Locally bundled open-license fonts
    package-lock.json
  backend/
    app/main.py                # Slim FastAPI entrypoint, middleware, and lifecycle (<100 lines)
    app/routes/                # Modular APIRouters (heat, models, simulation, optimization, risk, data, ai, reports)
    app/schemas.py             # Validated Pydantic v2 request/LLM schemas
    app/db.py                  # SQLAlchemy and PostGIS storage
    app/services/data.py       # Grid generation, feature indices, and fast caching
    app/services/sources.py    # Remote data adapters and quality processing (11 ingestion mechanisms)
    app/services/ml.py         # Dynamic spatial partitioning, training, persistence, and TreeSHAP
    app/services/planning.py   # Risk assessment, 8 intervention models, and CP-SAT optimizer
    app/services/ai.py         # Multi-provider assistant (Groq/Gemini/local) with numeric guardrails
    app/services/state.py      # Thread-safe city state management and caching
    tests/                     # Automated test suite (175 tests across unit, pipeline, sources, challenger, and E2E tiers)
    train.py                   # Synthetic / external labeled-data training CLI
    requirements.txt
  scripts/run-local.sh
  scripts/browser_smoke.py
  docs/METHODOLOGY.md
  docs/VERIFICATION.md
  TEST_INFRA.md
  TEST_READY.md
  Dockerfile
  compose.yaml
  .env.example
  pytest.ini
```

## 10 Canonical Views & Climate Intelligence UI

The frontend is built as a dark-first climate-intelligence platform (obsidian `#080c11`, slate surfaces `#0e141d`/`#121924`, hairline borders, monospace telemetry numerals, and Linear-level precision):

- **1. Overview Command Center (`OverviewPage.tsx`):** Municipal-level climate metrics (mean LST, max SUHII, population exposure, priority zones, and Earth Observation data provenance).
- **2. Live Environmental Map (`MapPage.tsx`):** Full multi-layer Leaflet GIS engine using CartoDB Dark Matter tiles, opacity controls, layer toggle stack (LST, SUHII, NDVI, Built-up, Population, Air Quality, Weather, Groundwater), physical-unit legends, and zone inspection flyout (preserving `sidecar://biomolecular_structure_viewer` link for raster layers).
- **3. Heat Analysis (`PredictionsPage.tsx` / `HeatPage`):** Defensible spatial ML tournament (Random Forest, XGBoost, LightGBM), test scatter plot, spatial partitioning visualization, and zone comparison matrix.
- **4. Environmental Analysis (`EnvironmentalPage.tsx`):** Dedicated environmental telemetry view showcasing Open-Meteo continuous weather time series, OpenAQ/CPCB air quality monitoring stations (PM2.5, PM10, NO2, SO2, O3, CO), and CGWB groundwater monitoring wells (depth in mbgl).
- **5. Heat Risk & Vulnerability (`RiskPage.tsx`):** Multi-factor transparent risk decomposition (Hazard × Exposure × Vulnerability) across municipal wards.
- **6. Explainable AI (`ExplainPage.tsx`):** Exact additive TreeSHAP global feature importance and zone-specific cooling/heating attributions.
- **7. Mitigation Planning (`SimulatorPage.tsx`):** Literature-grounded cooling simulation across eight interventions with physical constraints and uncertainty bounds.
- **8. Intervention Optimization (`OptimizerPage.tsx`):** Physical-only Google OR-Tools CP-SAT discrete combinatorial optimization (water limits, land-use ceilings, roof exclusivity, and cooling targets with zero budget constraints).
- **9. AI Climate Assistant (`AssistantPage.tsx`):** Multi-provider LLM assistant (Groq / Gemini) grounded strictly in backend analytical evidence with numeric guardrails and citations.
- **10. Reports & Data Export (`ReportsPage.tsx`):** Municipal summary generator with downloadable Markdown, CSV, and JSON audit packages.

### Navigation & Shell Features
- **Collapsible Application Shell (`Sidebar.tsx`):** Supports 240px expanded state, 64px icon-only rail with tooltips, and mobile drawer overlay with smooth transitions.
- **Omni-Search Command Palette (`CommandBar.tsx` / `Topbar.tsx`):** Press `Ctrl+K` or `⌘K` anywhere to search views, switch target cities (Ahmedabad, Delhi, Hyderabad), find zones, or toggle map layers.
- **Backward-Compatible Route Slugs:** Full support for canonical routes and legacy aliases (`overview`, `map`, `heat`, `prediction`, `compare`, `environmental`, `risk`, `explain`, `simulator`, `optimizer`, `assistant`, `reports`, `predictions`, `simulations`).

## Data integrations: actual status

| Source | Implemented | Verification in this environment |
|---|---|---|
| Open-Meteo forecast | Temperature, humidity, rainfall, wind, solar, soil moisture | Live success |
| Open-Meteo ERA5-Land historical | Date-bounded hourly variables | Live success, 48 hours retrieved |
| Earth Search Sentinel-2 L2A | Scene footprints, acquisition metadata, cloud filter | Live success, 4 qualifying scenes for Ahmedabad May 2025 |
| Sentinel-2 public COGs | Read real pixels, mask SCL, align EPSG:6933, NDVI/NDWI/NDBI | Live success, 1,024 valid 100 m pixels |
| OSM Overpass | Bounded roads/buildings/parks/water → GeoJSON | Conversion tested; live endpoint returned HTTP 406; mirror timed out |
| WorldPop | Population raster dataset catalog by country/year | Live success, one matching 2020 India catalog entry; rasters/demographics not processed |
| Earth Engine Landsat 8/9 | QA-masked LST and optical indices with date metadata | Implemented; live verification blocked by missing credentials |
| Earth Engine Sentinel-2 | SCL-masked optical indices | Implemented; credentials required |
| Earth Engine MODIS MOD11A2 | QA-filtered daytime LST composites | Implemented; credentials required |
| Earth Engine ESA WorldCover / SRTM | Separately dated land-cover/elevation samples | Implemented; credentials required |
| OpenAQ v3 | Optional monitoring-location lookup | API key required; pollutant readings not yet ingested |
| GHSL, Copernicus Data Space, NASA POWER, Google Maps | Optional | Not integrated |

The catalog and successful imports are persisted. Live imports **do not automatically produce validated heat predictions**. Only the synthetic demonstration model feeds the dashboard until an appropriately matched observed-label dataset is supplied and evaluated.

## Model results (measured synthetic spatial test set)

| Model | Test R² | Test RMSE °C | Test MAE °C |
|---|---:|---:|---:|
| Random Forest | 0.928722 | 0.511899 | 0.410495 |
| XGBoost | 0.942477 | 0.459863 | 0.368391 |
| LightGBM | 0.940034 | 0.469526 | 0.373430 |

LightGBM was selected by **validation** RMSE (0.497123°C), not test performance. The validation-residual band is ±0.899702°C. The split uses 162 training, 54 validation, 54 buffer and 54 test cells. Seeds/hyperparameters are in the methodology. These metrics are not real-world accuracy claims.

```bash
PYTHONPATH=backend .venv/bin/python backend/train.py --city Ahmedabad
```

To train an external dataset, prepare aligned WGS84 GeoJSON cells with all feature keys (documented in `data.py`), measured `lst` and matched `rural_reference`, and metadata `source`, `synthetic`, `acquisition_date`, `rural_method`, `crs`. At least 180 cells and at least 15 cells per spatial train/validation/test partition are required. Null feature values are allowed for median imputation. No data should contain target-derived predictors. This CLI is implemented but has **not** been validated with a real labeled training dataset.

```bash
PYTHONPATH=backend .venv/bin/python backend/train.py --city Ahmedabad --input /path/to/labeled.geojson
```

External models use a separate `*-external.joblib` namespace and do not overwrite dashboard demonstration models. Models are stored locally in `backend/models`; `MODEL_DIR` overrides the location. Do not load untrusted joblib files.

## Credentials and AI

Configure independently in `.env`:

```dotenv
GROQ_API_KEY=
GROQ_MODEL=
GEMINI_API_KEY=
GEMINI_MODEL=
EARTH_ENGINE_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=
OPENAQ_API_KEY=
API_TOKEN=
```

No model IDs are hardcoded. Choose a model available to your provider account; the adapter checks the provider's models endpoint before generation. Gemini model identifiers may be bare or prefixed `models/`. Earth Engine needs an enabled project and valid application credentials/service-account authorization. Keep `.env` and credential files out of Git and frontend bundles.

Groq/Gemini request/response handling, fallback and schema rejection were tested with mocked transports. **No live LLM generation was claimed or performed without keys.** LLM claims still need expert review; schema and source validation are not a proof of factual correctness. REDIS_URL and GOOGLE_MAPS_API_KEY are optional placeholders; this prototype uses bounded in-process caches and Leaflet, not Redis or Google Maps.

## API

Interactive schemas: `/docs`; OpenAPI JSON: `/openapi.json`.

- `GET /api/health`, `/api/cities`, `/api/overview`
- `POST /api/data/ingest`; `GET /api/data/status`, `/api/data/records`
- `POST /api/heat/predict`; `GET /api/heat/hotspots`, `/api/heat/map`
- `POST /api/models/train`; `GET /api/models`
- `POST /api/xai/explain`; `GET /api/xai/importance`
- `POST /api/risk/analyze`
- `GET /api/interventions`; `POST /api/simulation/run`; `GET /api/simulation/results`
- `POST /api/optimization/run`; `GET /api/optimization/results`
- `POST /api/ai/chat`
- `POST /api/reports/generate`; `GET /api/reports/{id}/download`, `/csv`, `/markdown`

Invalid ranges, coordinates, polygons, city IDs, zone IDs, intervention keys, duplicate optimizer zones and malformed LLM JSON are rejected. Network failures return explicit errors, never invented data. API calls are rate-limited in process; caches and rate limits are per worker. Historical weather accepts up to one year per request. Expensive ingestion/training is synchronous from the caller's perspective; production workloads need a job queue.

## Tests

```bash
# Run 175 automated backend tests (unit, pipeline, sources, API, challenger regression, E2E tiers 1-4):
pytest backend/tests/ -v

# Run 54 frontend Vitest component, utility, and API client tests:
npm --prefix frontend test -- --run

# Run TypeScript type check and production Vite bundle build:
npm --prefix frontend run build

# Optional automated Chromium tests, with the app running:
.venv/bin/python -m pip install playwright
.venv/bin/python scripts/browser_smoke.py
```

The repository root includes `pytest.ini`, so the backend suite is discovered automatically without needing to set `PYTHONPATH` manually. Fast startup and model persistence are enabled via environment variables (`FAST_STARTUP=1`, `PREWARM_STATE=0`), ensuring test suites execute in seconds.

Backend tests use their own temporary SQLite database and model directory, keeping mocked source data out of the actual workspace. PostgreSQL/PostGIS was separately tested against the running Docker database. Browser checks use `/usr/bin/chromium`; set `BROWSER_EXECUTABLE` for another installed Chromium. See `docs/VERIFICATION.md` for the executed checks and limitations.

## Remaining limits

This is a functioning **research MVP**, not the entire production research system. Unfinished or unvalidated parts include: real labeled heat-model calibration and external-data inference in the UI; live credentialed Earth Engine/Groq/Gemini execution; population-raster and age/sex ingestion; pollutant observation ingestion; optional GHSL/Copernicus/NASA POWER; measured intervention coefficients; multi-period historical heat trends; tree-count/roof-treatment convenience inputs (the simulator uses area coverage); full SHAP beeswarm plots (importance, local contribution, and spatial views are provided); city polygon drawing (GeoJSON entry is provided); multi-user authorization and production migrations/background jobs; operational object storage; full application Docker build; and hosted deployment. No completed-feature claim is made for these items.
