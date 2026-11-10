# Backend Architecture Survey Report

## 1. Observation

### 1.1 Backend Directory Layout and Root Configuration Files
- **Backend Directory Structure**:
  - `backend/app/`:
    - `main.py` (131 lines): Application entry point, lifespan, CORS, security middleware, error handlers, static asset serving, and APIRouter mounting.
    - `db.py` (84 lines): SQLAlchemy 2.0 ORM engine, connection configuration (SQLite/PostgreSQL PostGIS), metadata creation, and `Record`/`Zone` models.
    - `schemas.py` (200 lines): Pydantic v2 schemas (`StrictModel`, `AreaRequest`, `ZoneRequest`, `RiskRequest`, `SimulationRequest`, `OptimizationRequest`, `ChatRequest`, `AIResponse`, etc.).
    - `__init__.py`: Package init.
    - `routes/` (subdivided APIRouters):
      - `__init__.py`: Exports 8 routers (`heat_router`, `models_router`, `simulation_router`, `optimization_router`, `risk_router`, `data_router`, `ai_router`, `reports_router`).
      - `ai.py`, `data.py`, `heat.py`, `models.py`, `optimization.py`, `reports.py`, `risk.py`, `simulation.py`.
    - `services/`:
      - `ai.py` (270 lines): Direct LLM API client (Groq/Gemini via HTTPX), prompt grounding, numeric measurement guardrails regex, and local fallback.
      - `data.py` (193 lines): Synthetic city generator `sample_data()`, database persistence `persist_dataset()`, coordinate constants `CITIES`.
      - `ml.py` (338 lines): Generalized spatial partitioning `assign_spatial_partitions()`, model tournament (RandomForest, XGBoost, LightGBM), inference, and TreeSHAP.
      - `planning.py` (409 lines): Cooling intervention models, surface capacity checks, OR-Tools CP-SAT discrete optimizer, and the `risk()` calculation function (lines 140–160).
      - `sources.py` (769 lines): 11 live data adapters (Open-Meteo, NASA POWER, OSM Overpass, WorldPop, OpenAQ, Sentinel-2 STAC/COG, Copernicus, GHSL, Google Earth Engine, OSM Tile Proxy).
      - `state.py` (85 lines): Thread-safe state store `STATE` with `threading.RLock()`, lazy loader `state(city)`, `zone()`, and `get_city_overview()`.
  - **Notable Directory Absences**:
    - Neither `backend/app/routers/` nor `backend/app/api/` exists; the directory is named `backend/app/routes/`.
    - Neither `backend/app/services/llm/` nor `backend/app/schemas/ai.py` exists; LLM code is entirely in `services/ai.py` and schemas in `schemas.py`.
    - Neither `backend/app/services/demographics.py`, `backend/app/services/satellite.py`, `backend/app/services/geospatial.py`, `backend/app/services/features.py`, `backend/app/services/xai.py`, `backend/app/services/optimization.py`, nor `backend/app/services/risk.py` exists as a separate file.
- **Root Configuration Files**:
  - `backend/requirements.txt`: 20 requirements: `fastapi>=0.115,<1`, `uvicorn>=0.34,<1`, `pydantic>=2.10,<3`, `sqlalchemy>=2.0,<3`, `psycopg[binary]>=3.2,<4`, `geoalchemy2>=0.17,<1`, `numpy>=2,<3`, `pandas>=2.2,<4`, `scikit-learn>=1.6,<2`, `xgboost-cpu>=3,<4`, `lightgbm>=4,<5`, `shap>=0.49,<1`, `scipy>=1.15,<2`, `ortools>=9.12,<10`, `geopandas>=1,<2`, `rasterio>=1.4,<2`, `httpx>=0.28,<1`, `python-dotenv>=1,<2`, `earthengine-api>=1,<2`, `pytest>=8,<10`.
  - `pyproject.toml`: Neither root nor `backend/` has a `pyproject.toml`.
  - `pytest.ini`:
    ```ini
    [pytest]
    pythonpath = backend
    testpaths = backend/tests
    asyncio_default_fixture_loop_scope = function
    ```
  - `.env` & `.env.example`: Provides `DATABASE_URL`, `GROQ_API_KEY`, `GROQ_MODEL` (`llama-3.3-70b-versatile`), `GEMINI_API_KEY`, `GEMINI_MODEL` (`gemini-3.8-flash`), `EARTH_ENGINE_PROJECT` (`sai-gae-app-2026`), `GOOGLE_MAPS_API_KEY`, `OPENAQ_API_KEY`, `REDIS_URL`, and `API_TOKEN`.
  - `Dockerfile`: Multi-stage build (stage 1: `node:22-bookworm-slim` building frontend; stage 2: `python:3.12-slim` installing `backend/requirements.txt`, copying `frontend/dist` into `./frontend/dist`, and launching `uvicorn app.main:app`).
  - `compose.yaml`: Runs `db` service (`postgis/postgis:16-3.4-alpine`, port 5433) and `app` service (`DATABASE_URL: postgresql+psycopg://heatwise:${POSTGRES_PASSWORD:-heatwise}@db:5432/heatwise`).

---

### 1.2 Routing Structure and Frontend/Backend Route Consistency
- **Mounting in `backend/app/main.py`**:
  - Root routes in `main.py`:
    - Line 93: `@app.get("/api/health", response_model=HealthResponse, tags=["system"])`
    - Line 100: `@app.get("/api/tiles/{z}/{x}/{y}.png", tags=["tiles"])`
    - Line 129: `@app.get("/")` serving `frontend/dist/index.html`
    - Line 127: `app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")`
  - Router registration (Lines 122–123):
    ```python
    for r in (heat_router, models_router, simulation_router, optimization_router, risk_router, data_router, ai_router, reports_router):
        app.include_router(r)
    ```
    Note: Routers are mounted **without** any top-level `prefix="/api"`.
- **Router Prefixes Asymmetry**:
  - 5 routers define `prefix="/api/..."` on `APIRouter()`:
    - `app/routes/data.py:13`: `APIRouter(prefix="/api/data", tags=["data"])` (endpoints: `/status`, `/records`, `/series`, `/ingest`)
    - `app/routes/optimization.py:10`: `APIRouter(prefix="/api/optimization", tags=["optimization"])` (endpoints: `/run`, `/results`)
    - `app/routes/risk.py:9`: `APIRouter(prefix="/api/risk", tags=["risk"])` (endpoint: `/analyze`)
    - `app/routes/ai.py:10`: `APIRouter(prefix="/api/ai", tags=["ai"])` (endpoint: `/chat`)
    - `app/routes/reports.py:13`: `APIRouter(prefix="/api/reports", tags=["reports"])` (endpoints: `/generate`, `/{id}/download`, `/{id}/csv`, `/{id}/markdown`)
  - 3 routers define `prefix=""` (or omitted) and hardcode `"/api/..."` on every route decorator:
    - `app/routes/heat.py:9`: `APIRouter(tags=["heat"])`
      - Line 12: `@router.get("/api/cities")`
      - Line 18: `@router.get("/api/overview")`
      - Line 24: `@router.get("/api/heat/map")`
      - Line 30: `@router.get("/api/heat/hotspots")`
      - Line 40: `@router.post("/api/heat/predict")`
    - `app/routes/models.py:9`: `APIRouter(tags=["models", "xai"])`
      - Line 12: `@router.get("/api/models")`
      - Line 18: `@router.post("/api/models/train")`
      - Line 26: `@router.post("/api/xai/explain")`
      - Line 39: `@router.get("/api/xai/importance")`
    - `app/routes/simulation.py:10`: `APIRouter(tags=["simulation"])`
      - Line 13: `@router.get("/api/interventions")`
      - Line 19: `@router.post("/api/simulation/run")`
      - Line 47: `@router.get("/api/simulation/results")`
- **Frontend URL Mapping**:
  - `frontend/src/services/apiClient.ts:74`: `response = await fetch("/api" + path, ...)`
  - Frontend services call:
    - `heatService`: `/health`, `/cities`, `/overview`, `/heat/map`, `/heat/hotspots`, `/heat/predict`
    - `dataService`: `/data/status`, `/data/records`, `/data/ingest`
    - `weatherService`: `/data/series`
    - `mlService`: `/models`, `/models/train`, `/xai/explain`, `/xai/importance`
    - `simulationService`: `/interventions`, `/simulation/run`, `/simulation/results`
    - `optimizationService`: `/optimization/run`, `/optimization/results`
    - `riskService`: `/risk/analyze`
    - `aiService`: `/ai/chat`
    - `reportService`: `/reports/generate`, `/reports/{id}/download`, etc.
  - Runtime match: Every single frontend service call prepends `"/api"` and hits an exact matching route on the backend.
  - Refactoring trap: If an engineer attempts to mount routers in `main.py` using `app.include_router(heat_router, prefix="/api")`, it will result in `/api/api/cities`, `/api/api/overview`, etc., breaking all frontend calls.

---

### 1.3 Missing Risk Module & Import Coupling
- **Status of `backend/app/services/risk.py`**:
  - File does NOT exist (`Test-Path` returned `False`).
- **Where `risk()` is implemented**:
  - `backend/app/services/planning.py:140-160`:
    ```python
    def risk(p, weights=(1, 1, 1)):
        hazard = min(1, max(0, p.get("predicted_suhii", p.get("observed_suhii", 2.0))) / 8)
        exposure = min(1, p["population_density"] / 25000)
        vulnerability = min(1, p["elderly_share"] / 0.25)
        value = (
            100
            * hazard ** weights[0]
            * exposure ** weights[1]
            * vulnerability ** weights[2]
        )
        return {
            "risk_score": value,
            "hazard": hazard,
            "exposure": exposure,
            "vulnerability": vulnerability,
            "risk_level": "High" if value >= 20 else "Moderate" if value >= 8 else "Low",
            "missing_indicators": [
                "Socioeconomic status",
                "Health conditions",
                "Access to cooling",
            ],
        }
    ```
- **Import references to `risk`**:
  - `backend/app/routes/risk.py:6`: `from app.services.planning import risk`
  - `backend/app/services/state.py:11`: `from app.services.planning import risk`
  - `backend/app/services/planning.py:367`: calls `risk(p)["risk_score"]` internally in optimization
  - `backend/tests/test_pipeline.py:16, 82`: imports and tests `risk()`
  - `backend/tests/test_e2e_tiers.py:986`: exercises risk workflow
- **Dependency coupling**:
  - `planning.py` combines physical intervention simulation, CP-SAT discrete optimization, and climate vulnerability assessment in a single 409-line file.
  - Agent 2 (Demographic Data and Vulnerability Engineer) has primary ownership of `backend/app/services/risk.py`, which is currently missing.

---

### 1.4 Database Configuration and ORM Models
- **Database Engine & Connection (`backend/app/db.py`)**:
  - `URL = os.getenv("DATABASE_URL") or f"sqlite:///{ROOT}/data/heatwise.db"`
  - `POSTGIS = URL.startswith("postgresql")`
  - SQLite configuration: `connect_args={"check_same_thread": False}`.
  - PostgreSQL configuration: Uses `psycopg` 3 (`postgresql+psycopg://...`), `pool_pre_ping=True`.
  - PostGIS Extension Initialization:
    ```python
    def init_db():
        if POSTGIS:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        Base.metadata.create_all(engine)
    ```
- **ORM Models**:
  - `Record` (table: `analysis_records`):
    - `id: Mapped[str]` (primary key, UUID or user-provided)
    - `kind: Mapped[str]` (indexed; values: `"weather"`, `"osm"`, `"satellite"`, `"monitoring"`, `"scenario"`, `"optimization"`, `"risk"`, `"report"`, `"conversation"`, `"dataset"`)
    - `payload: Mapped[dict] = mapped_column(JSON)` (polymorphic document payload)
    - `created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))`
  - `Zone` (table: `zones`):
    - `id: Mapped[str]` (primary key)
    - `city: Mapped[str]` (indexed)
    - `properties: Mapped[dict] = mapped_column(JSON)`
    - `boundary = mapped_column(Geometry("POLYGON", srid=4326) if POSTGIS else Text)`
- **Migrations**:
  - No Alembic or external migration system is installed or configured. Schema is created dynamically on app startup via `Base.metadata.create_all(engine)`.

---

### 1.5 Test Infrastructure (`backend/tests/`)
- **Test Modules**:
  1. `conftest.py` (123 lines):
     - Sets `TESTING=1`, `FAST_STARTUP=1`, `PREWARM_STATE=0`, `API_TOKEN=""`.
     - Windows Sandbox IOCP Proactor Patch (`_safe_set_wakeup_fd`, `_DummySocket`, `_make_self_pipe`, `_safe_poll`) to eliminate Windows socketpair connect hangs in sandbox.
     - Creates isolated `tempfile.TemporaryDirectory` for SQLite database (`tests.db`), `models/`, and `mpl/` Matplotlib config.
     - Copies pre-trained `.joblib` models into temp directory.
     - Provides autouse fixture `reset_rate_limit` to reset `main.RATE`.
  2. `test_ai.py` (1 test): Validates provider schema, findings fact citation, and prompt contract.
  3. `test_api.py` (5 tests): Integrated end-to-end API workflow, validation error handling, unconfigured provider fallback, API token security, upstream 502 handling.
  4. `test_challenger_m2.py` (28 tests): Stress testing spatial clustering (KMeans, quantiles, collinear coordinates, concentric rings, zero area), custom partitions, and AI numeric guardrails regex.
  5. `test_challenger_m2_api_budget.py` (20 tests): CP-SAT solver budget boundaries, multithreaded state concurrency, cold start, and router edge cases.
  6. `test_e2e_tiers.py` (78 tests): Tier 1 (50 feature coverage tests across 10 domains), Tier 2 (22 boundary/corner tests), Tier 3 (3 cross-feature workflows), Tier 4 (3 real-world climate scenarios).
  7. `test_foundation.py` (3 tests): Health endpoint, synthetic provenance & geometry, spectral indices & cloud masking.
  8. `test_pipeline.py` (6 tests): Spatial CV holdout evaluation, TreeSHAP additivity, physical simulation constraints, optimizer constraints, convenience input conversion, and risk scoring.
  9. `test_sources.py` (34 tests): Comprehensive unit tests for all 11 live data adapters, OSM mirror failovers, OpenAQ error handling, and caching.
- **Execution Command and Test Results**:
  - Test command: `pytest -q`
  - Collected tests: 175 tests across 8 test modules.
  - Execution result: **175 passed, 15 warnings in 45.35s** (exit code 0).

---

### 1.6 GenAI and LLM Services Structure
- **Module Location**:
  - `backend/app/services/ai.py` (270 lines).
  - No `services/llm/` directory exists.
  - No `schemas/ai.py` exists; schemas (`ChatRequest`, `AIFinding`, `AIResponse`, `ChatResponse`) reside in `backend/app/schemas.py`.
- **Implementation Mechanism**:
  - Direct async HTTP requests via `httpx.AsyncClient` without vendor SDKs (`google-generativeai` or `groq` packages are not in `requirements.txt`).
  - **Groq Integration**:
    - Discovers models via `GET https://api.groq.com/openai/v1/models`.
    - Generates responses via `POST https://api.groq.com/openai/v1/chat/completions` with `json_object` format and temperature 0.1.
  - **Gemini Integration**:
    - Discovers models via `GET https://generativelanguage.googleapis.com/v1beta/models`.
    - Generates responses via `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` with `responseMimeType: "application/json"`.
  - **Fact Grounding & Numeric Guardrails**:
    - Strict system prompt mandating JSON adherence to schema.
    - `extract_numbers_from_facts(facts)`: Extracts all finite float/int numbers from supplied zone facts.
    - `ENTITY_WHITELIST`: Whitelists benign domain entities (e.g., `Sentinel-2`, `Landsat-8`, `PM2.5`, `H3-8`, `10 m`, `5 km`).
    - `NUMERIC_MEASUREMENT_PATTERN`: Atomic lookahead regex capturing measurements (`°C`, `%`, `m³/day`, `USD`, `INR`) without catastrophic backtracking.
    - Validation: Every extracted number in LLM prose must match a fact within tolerance (0.15 absolute or 5% relative, exact match for 0). If unsupported, raises `ValueError`.
    - Action feasibility validation: Any recommended action must pass `simulate(p, {action: 5})["feasible"]`.
  - **Multi-Provider Fallback**:
    - Order: Specified provider (`groq` or `gemini`) -> alternative provider -> deterministic `local evidence summary` template (`fallback: True`).

---

## 2. Logic Chain

1. **Backend Routing Architecture**:
   - Observation 1.2 shows that `main.py` mounts routers via `app.include_router(r)` without a prefix.
   - Observation 1.2 shows that `heat_router`, `models_router`, and `simulation_router` hardcode `"/api/..."` in their path decorators (`@router.get("/api/cities")`), whereas `data_router`, `optimization_router`, `risk_router`, `ai_router`, and `reports_router` declare `prefix="/api/..."` on their `APIRouter` instances.
   - Observation 1.2 shows that `frontend/src/services/apiClient.ts` prepends `"/api"` to every request path.
   - Reasoning: Although all frontend requests currently match backend endpoints at runtime, the backend router declarations are inconsistent. Any future refactoring to standardize router mounting (e.g. mounting with `prefix="/api"` at the app level) would create duplicate prefixes (`/api/api/cities`) unless the router path decorators are also refactored to remove the redundant `"/api"`.
   - Furthermore, the code directory is `backend/app/routes/`, whereas the Original Request assigned `backend/app/api/` and `backend/app/routers/` to Agent 6. The team must either retain `routes/` or create compatibility re-exports to avoid broken imports.

2. **Missing Risk Module**:
   - Observation 1.3 shows that `backend/app/services/risk.py` does not exist.
   - Observation 1.3 shows that the core `risk()` function is defined in `backend/app/services/planning.py:140–160` and imported by `routes/risk.py` and `services/state.py`.
   - Reasoning: Placing demographic vulnerability and hazard risk scoring inside `planning.py` violates modular separation of concerns. Extracting `risk()` into `backend/app/services/risk.py` (owned by Agent 2) will clean up service boundaries. However, to preserve compatibility with existing imports in `planning.py`, `state.py`, `routes/risk.py`, and test files, `planning.py` should re-export `risk` (`from app.services.risk import risk`) during the migration.

3. **Database and ORM Design**:
   - Observation 1.4 reveals a flexible hybrid database design: SQLite local fallback with automatic PostGIS spatial support when `DATABASE_URL` begins with `postgresql`.
   - The ORM uses a polymorphic `Record` table with a JSON payload column. This allows rapid persistence of diverse data structures (`"weather"`, `"satellite"`, `"optimization"`, `"scenario"`) without requiring schema migrations.
   - Dynamic schema generation via `Base.metadata.create_all(engine)` is appropriate for the current MVP and testing setup, eliminating migration friction during multi-agent development.

4. **Test Suite Health and Performance**:
   - Observation 1.5 shows that the test suite is exceptionally healthy, with all 175 tests passing in ~45 seconds.
   - The test infrastructure in `conftest.py` already solves key Windows and environment challenges (Windows Proactor IOCP patch, isolated temp SQLite DB, fast startup flags, model caching).
   - Any multi-agent modifications to backend services or schemas can be immediately verified against this 175-test regression baseline.

5. **GenAI Architecture Readiness**:
   - Observation 1.6 shows that LLM calls are implemented cleanly via direct `httpx` calls without bulky SDKs.
   - Grounding guardrails (TreeSHAP fact injection, regex-based numeric audit, feasibility verification) are already robust and covered by challenger tests.
   - To align with the Original Request's architecture for Agent 5, `services/ai.py` can be refactored into modular components under `backend/app/services/llm/` (e.g., `groq_client.py`, `gemini_client.py`, `guardrails.py`, `fallback.py`) and schemas separated into `backend/app/schemas/ai.py`, provided that re-exports are maintained in `services/ai.py`.

---

## 3. Caveats

- **External Live Services**: In the test environment, `TESTING=1` is set, and external live endpoints (Open-Meteo, NASA POWER, Sentinel STAC, Groq, Gemini) are mocked or fall back to local implementations. Live integration tests requiring outbound network access or active API tokens should be tested separately with real environment variables.
- **PostGIS vs SQLite**: Test execution runs against the SQLite local fallback (`connect_args={"check_same_thread": False}`). While PostGIS spatial geometry is defined in `Zone.boundary`, full spatial SQL queries (e.g. `ST_Contains`) require a running PostgreSQL/PostGIS container as defined in `compose.yaml`.

---

## 4. Conclusion

1. **Routing**: The backend routing matches all 26 frontend endpoints cleanly at runtime, but suffers from internal declaration asymmetry (3 routers hardcode `/api` in route paths, 5 routers use router prefixes). The directory is `backend/app/routes/`.
2. **Missing Modules**: `backend/app/services/risk.py` is absent; the `risk()` function is housed in `backend/app/services/planning.py`. It should be extracted to `backend/app/services/risk.py` with backward-compatible re-exports.
3. **Database**: Robust dual-mode (SQLite fallback + PostgreSQL/PostGIS) with SQLAlchemy 2.0 and JSON document persistence. No migration issues exist.
4. **Testing Baseline**: 175 tests across 8 test suites pass with 100% success rate in 45 seconds. This provides a rock-solid regression safety net.
5. **GenAI**: Robust, guardrail-protected HTTP client for Groq and Gemini in `services/ai.py` ready for modular extraction into `backend/app/services/llm/` and `backend/app/schemas/ai.py`.

---

## 5. Verification Method

To independently verify all findings and test suite execution:

1. **Run Full Test Suite**:
   ```powershell
   pytest -q
   ```
   *Expected outcome*: `175 passed` with exit code 0.

2. **Verify Route Inconsistency and Hardcoded `/api`**:
   ```powershell
   Select-String -Path "backend/app/routes/*.py" -Pattern 'router = APIRouter'
   Select-String -Path "backend/app/routes/*.py" -Pattern '@router\.(get|post)\("/api/'
   ```
   *Observation*: Confirms `heat.py`, `models.py`, and `simulation.py` omit prefix and hardcode `/api/`.

3. **Verify Missing `services/risk.py` and Location of `risk()`**:
   ```powershell
   Test-Path "backend/app/services/risk.py"
   Select-String -Path "backend/app/services/planning.py" -Pattern "def risk\("
   ```
   *Observation*: `Test-Path` returns `False`, while `planning.py:140` defines `def risk(p, weights=(1, 1, 1)):`.

4. **Verify Database Configuration**:
   ```powershell
   Get-Content "backend/app/db.py" | Select-String -Pattern "(URL =|POSTGIS =|class Record|class Zone|def init_db)"
   ```

5. **Verify AI Guardrails & Provider Status**:
   ```powershell
   pytest backend/tests/test_ai.py backend/tests/test_challenger_m2.py -k "guardrails" -q
   ```
   *Expected outcome*: All guardrail and validation tests pass.
