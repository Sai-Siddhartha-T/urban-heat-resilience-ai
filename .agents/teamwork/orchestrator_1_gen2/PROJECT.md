# Project: AI-Powered Urban Heat Resilience & Mitigation Platform

## Architecture
- **Backend Architecture**: FastAPI asynchronous REST API, SQLAlchemy 2.0 ORM with SQLite local fallback and PostGIS spatial support. Strict Pydantic v2 schemas (`extra="forbid", allow_inf_nan=False`).
- **ML Pipeline Architecture**: Spatial cross-validation with 6 longitude-based spatial blocks (train=50%, val=16.7%, spatial buffer=16.7%, test=16.7%). Model tournament across Random Forest, XGBoost, and LightGBM with lowest RMSE winner selection. Exact additive TreeSHAP explainability.
- **Simulation & Optimization Architecture**: 8 intervention models (trees, vegetation, parks, cool roofs, pavements, corridors, roof gardens, water) with physical surface capacity and water limits. Combinatorial multi-objective discrete optimization via Google OR-Tools CP-SAT solver with 50% water sensitivity alternative.
- **External Integration Architecture**: 11 data source ingestion mechanisms in `backend/app/services/sources.py` (Open-Meteo, NASA POWER, OSM Overpass with dual mirrors, WorldPop STAC, OpenAQ v3, Sentinel-2 STAC/COG with WarpedVRT windowing, Copernicus STAC, GHSL STAC, Google Earth Engine, OSM Tile Proxy). Strict provenance (HTTP 502 on live failure, zero synthetic masquerading). Multi-provider AI assistant (Groq/Gemini fallback) with citation verification and numeric guardrails.
- **Frontend Architecture**: React 19 + TypeScript + Vite + Tailwind CSS. Decomposed from 2,164-line monolithic `App.tsx` into clean modular pages (`src/pages/*`), reusable components (`src/components/*`), strict domain types (`src/types/*`), and dedicated services (`src/services/*`). Clean routing and Vitest testing suite.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Frontend Monolith Decomposition | Split 2,164-line `App.tsx` into modular pages and components | M1 | Survey 1 |
| 2 | Strict TypeScript Types | Define domain interfaces (`geojson.ts`, `simulation.ts`, `weather.ts`, `optimization.ts`, `chat.ts`) removing all `any` | M1 | Survey 1 |
| 3 | Dedicated Frontend Services | Refactor `api.ts` into strongly-typed client modules | M1 | Survey 1 |
| 4 | Zone Comparison View | Multi-zone selection and side-by-side metric comparison table & charts | M1 | Survey 1 |
| 5 | Weather Time-Series Visualization | Render hourly/daily Open-Meteo temperature & humidity charts using Recharts | M1 | Survey 1 |
| 6 | Polygon Boundary Sketch Activation | Re-integrate `BoundarySketch.tsx` into `DataDialog` for interactive drawing | M1 | Survey 1 |
| 7 | Dead Code & Icon Cleanup | Remove unused imports and wire up orphaned queries | M1 | Survey 1 |
| 8 | Ingestion Source Dropdown Parity | Add NASA POWER, Copernicus, and GHSL options to frontend ingestion modal | M1 | Survey 1 & 3 |
| 9 | Frontend Vitest Test Suite | Establish unit and component tests in `frontend/src/tests/` so `npm test` passes cleanly | M1 | Survey 1 & 3 |
| 10 | Frontend Code-Splitting & Build | Verify clean TypeScript build (`npm run build`) with modular chunks | M1 | Survey 1 |
| 11 | Backend APIRouter Modularization | Split 602-line `main.py` into dedicated routers in `backend/app/routes/` | M2 | Survey 2 |
| 12 | ML State Caching & Startup Optimization | Persist/cache trained models to avoid 540-tree cold-start training bottleneck | M2 | Survey 2 & 3 |
| 13 | Spatial Clustering Generalization | Enable coordinate-based spatial clustering for arbitrary GeoJSON boundaries | M2 | Survey 2 |
| 14 | AI Guardrail Regex Refinement | Refine regex to target physical measurement units without false-positive fallbacks | M2 | Survey 2 |
| 15 | Optimizer Financial Budget Constraints | Add CapEx/OpEx financial budget parameter to CP-SAT optimizer | M2 | Survey 2 |
| 16 | Adapter Unit Test Expansion | Add unit tests for Open-Meteo, OpenAQ, WorldPop, GHSL, Sentinel-2 COG, and Earth Engine | M2 | Survey 3 |
| 17 | E2E Test Infrastructure | Design standalone runner, fixtures, and assertions for Tiers 1-4 | E2E Track | Survey 3 |
| 18 | Tier 1: Feature Coverage Tests | >=5 test cases per feature across endpoints, adapters, and UI | E2E Track | Survey 3 |
| 19 | Tier 2: Boundary & Corner Cases | Coordinate limits, zero denominators, mirror failover, rate limits | E2E Track | Survey 3 |
| 20 | Tier 3: Cross-Feature Workflows | Ingest -> Predict -> SHAP -> Risk -> Optimize -> AI Chat -> Export | E2E Track | Survey 3 |
| 21 | Tier 4: Real-World Scenarios | End-to-end municipal climate resilience planning scenario | E2E Track | Survey 3 |
| 22 | Final E2E Suite Pass & Verification | Run and pass 100% of Tiers 1-4 test suite | M3 (Final) | Survey 3 |
| 23 | Adversarial Coverage Hardening | White-box stress testing and edge-case hardening (Tier 5) | M3 (Final) | Survey 3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Frontend Modularization & Enhancements | Split App.tsx, strict types, zone comparison, weather series, BoundarySketch activation, Vitest tests, clean build | None | IN_PROGRESS (Iter 2) |
| M2 | Backend Modularization, ML & Integration Enhancements | Modular APIRouters, state caching/fast startup, spatial clustering, AI regex refinement, optimizer budget limits, adapter test expansion | None | PLANNED |
| E2E | E2E Testing Track | Design and build comprehensive opaque-box test suite (Tiers 1-4) published via TEST_READY.md | None | PLANNED |
| M3 | Final E2E Test Pass & Adversarial Hardening | Phase 1: 100% E2E test pass across Tiers 1-4. Phase 2: Tier 5 adversarial coverage hardening | M1, M2, E2E | PLANNED |

---

## Interface Contracts

### 1. Spatial Heat & Prediction Contract
- `POST /api/heat/predict`
  - Request: `ZoneRequest(city: str, properties: dict[str, float])`
  - Response: `PredictionResponse(predicted_suhii: float, interval_lower: float, interval_upper: float, confidence: float, model_used: str, base_value: float, contributions: dict[str, float])`

### 2. Intervention Simulation Contract
- `POST /api/simulation/run`
  - Request: `SimulationRequest(zone_properties: dict, interventions: dict[str, float])`
  - Response: `SimulationResponse(cooling_celsius: float, water_m3_day: float, feasible: bool, warnings: list[str], metrics_delta: dict[str, float])`

### 3. CP-SAT Optimization Contract
- `POST /api/optimization/run`
  - Request: `OptimizationRequest(zones: list[dict], water_limit: float, budget_limit: float | None = None)`
  - Response: `OptimizationResponse(status: str, total_cooling: float, water_used: float, budget_used: float | None, allocations: dict[str, dict[str, float]], sensitivity_50pct_water: dict)`

### 4. Weather & Time-Series Contract
- `GET /api/data/series?city=Ahmedabad`
  - Response: `dict(series: list[dict(timestamp: str, temperature_2m: float, relative_humidity_2m: float, precipitation: float, surface_solar_radiation: float)])`

### 5. AI Assistant Contract
- `POST /api/ai/chat`
  - Request: `ChatRequest(message: str, zone_id: str | None, context: dict | None)`
  - Response: `ChatResponse(response: str, citations: list[str], provider: str)`

---

## Code Layout
- `backend/app/main.py`: FastAPI entrypoint, middleware, lifecycle
- `backend/app/routes/`: Subdivided APIRouters (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`)
- `backend/app/schemas.py`: Pydantic models
- `backend/app/services/`: Core logic (`ml.py`, `planning.py`, `data.py`, `sources.py`, `ai.py`)
- `backend/app/db.py`: Database models and connection
- `backend/tests/`: Pytest suite (foundation, pipeline, ai, api, sources, e2e)
- `frontend/src/App.tsx`: Clean top-level orchestrator (<150 lines, currently 86 lines)
- `frontend/src/pages/`: Modular page views (`OverviewPage`, `MapPage`, `PredictionsPage`, `ExplainPage`, `RiskPage`, `SimulatorPage`, `OptimizerPage`, `AssistantPage`, `ReportsPage`, `ZoneComparePage`)
- `frontend/src/components/`: Reusable components (`common/`, `layout/`, `map/`, `charts/`, `zone/`, `modals/`)
- `frontend/src/types/`: Strict TypeScript domain interfaces
- `frontend/src/services/`: Strongly-typed API client services
- `frontend/src/tests/`: Vitest unit and component tests
