# Project: AI-Powered Urban Heat Resilience & Mitigation Platform

## Architecture
- **Backend Architecture**: FastAPI asynchronous REST API, SQLAlchemy 2.0 ORM with SQLite local fallback and PostGIS spatial support. Strict Pydantic v2 schemas (`extra="forbid", allow_inf_nan=False`). Subdivided into 8 domain-specific APIRouters in `backend/app/routes/` and a thread-safe decoupled state store in `backend/app/services/state.py`.
- **ML Pipeline Architecture**: Spatial cross-validation with generalized coordinate-based 2D KMeans clustering and quantile fallbacks (`assign_spatial_partitions()`). Preserves exact legacy 6-block split (`training: 162, validation: 54, test: 54, buffer: 54`) for municipal baseline datasets. Model tournament across Random Forest, XGBoost, and LightGBM with lowest RMSE winner selection. Exact additive TreeSHAP explainability down to $\Delta < 10^{-6}$.
- **Simulation & Optimization Architecture**: 8 intervention models (trees, vegetation, parks, cool roofs, pavements, corridors, roof gardens, water) with physical surface capacity, water limits, and municipal CapEx/OpEx financial budget constraints. Combinatorial discrete optimization via Google OR-Tools CP-SAT solver with integer constraints and 50% water sensitivity contingency.
- **External Integration Architecture**: 11 data source ingestion mechanisms in `backend/app/services/sources.py` (Open-Meteo, NASA POWER, OSM Overpass with dual mirrors, WorldPop STAC, OpenAQ v3, Sentinel-2 STAC/COG with WarpedVRT windowing, Copernicus STAC, GHSL STAC, Google Earth Engine, OSM Tile Proxy). Strict provenance (HTTP 502 on live failure, zero synthetic masquerading). Multi-provider AI assistant with atomic regex measurement validation, entity resolution whitelisting, and strict fact grounding.
- **Frontend Architecture**: React 19 + TypeScript + Vite + Tailwind CSS. Decomposed from 2,164-line monolithic `App.tsx` down to 101 lines (<150 limit) using clean hash routing (`useHashRouter.ts`). 10 modular page views (`src/pages/*`), reusable components (`src/components/*`), strict domain types without `: any` (`src/types/*`), and dedicated API client services (`src/services/*`). Complete unit/integration tests in Vitest and clean production build.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | Frontend Monolith Decomposition | Split 2,164-line `App.tsx` into modular pages and components (<150 lines) | M1 | Survey 1 | DONE |
| 2 | Strict TypeScript Types | Define domain interfaces (`geojson.ts`, `simulation.ts`, `weather.ts`, `optimization.ts`, `chat.ts`) removing all `any` | M1 | Survey 1 | DONE |
| 3 | Dedicated Frontend Services | Refactor `api.ts` into strongly-typed client modules wrapping `/api/*` with `ApiError` | M1 | Survey 1 | DONE |
| 4 | Zone Comparison View | Multi-zone selection and side-by-side metric comparison table & Recharts | M1 | Survey 1 | DONE |
| 5 | Weather Time-Series Visualization | Render hourly/daily Open-Meteo temperature & humidity charts using Recharts | M1 | Survey 1 | DONE |
| 6 | Polygon Boundary Sketch Activation | Re-integrate `BoundarySketch.tsx` into `DataDialog` for interactive drawing | M1 | Survey 1 | DONE |
| 7 | Dead Code & Icon Cleanup | Remove unused imports and wire up orphaned queries | M1 | Survey 1 | DONE |
| 8 | Ingestion Source Dropdown Parity | Add NASA POWER, Copernicus, and GHSL options to frontend ingestion modal | M1 | Survey 1 & 3 | DONE |
| 9 | Frontend Vitest Test Suite | Establish unit and component tests in `frontend/src/tests/` so `npm test` passes cleanly | M1 | Survey 1 & 3 | DONE |
| 10 | Frontend Code-Splitting & Build | Verify clean TypeScript build (`tsc -b && vite build`) with exit code 0 | M1 | Survey 1 | DONE |
| 11 | Backend APIRouter Modularization | Split `main.py` (99 SLOC) into 8 dedicated routers in `backend/app/routes/` with re-exports | M2 | Survey 2 | DONE |
| 12 | ML State Caching & Startup Optimization | Persist/cache trained models to avoid cold-start training bottleneck (`FAST_STARTUP=1`) | M2 | Survey 2 & 3 | DONE |
| 13 | Spatial Clustering Generalization | Enable dynamic 2D KMeans coordinate clustering for arbitrary GeoJSON boundaries | M2 | Survey 2 | DONE |
| 14 | AI Guardrail Regex Refinement | Atomic lookahead capture, metric resolution tokens, scientific notation, zero-rounding elimination | M2 | Survey 2 | DONE |
| 15 | Optimizer Financial Budget Constraints | Add CapEx/OpEx financial budget parameter to OR-Tools CP-SAT optimizer | M2 | Survey 2 | DONE |
| 16 | Adapter Unit Test Expansion | Add 34 unit tests covering all 11 sources, OSM failover, and OpenAQ resilience | M2 | Survey 3 | DONE |
| 17 | E2E Test Infrastructure | Design standalone runner, fixtures, and assertions for Tiers 1-4 (`TEST_INFRA.md`) | E2E Track | Survey 3 | DONE |
| 18 | Tier 1: Feature Coverage Tests | 50 test cases (5 per feature area across all 10 platform domains) | E2E Track | Survey 3 | DONE |
| 19 | Tier 2: Boundary & Corner Cases | 22 test cases covering coordinate limits, budget extremes, zero water, SSRF | E2E Track | Survey 3 | DONE |
| 20 | Tier 3: Cross-Feature Workflows | 3 test cases for multi-step pipeline integration workflows | E2E Track | Survey 3 | DONE |
| 21 | Tier 4: Real-World Scenarios | 3 municipal climate resilience scenarios (Ahmedabad, rapid urbanization, industrial corridor) | E2E Track | Survey 3 | DONE |
| 22 | Final E2E Suite Pass & Verification | Verify 100% of E2E test suite (78 tests) passes cleanly | M3 (Final) | Survey 3 | IN_PROGRESS |
| 23 | Adversarial Coverage Hardening | White-box stress testing, challenger test suite integration, and edge-case hardening (Tier 5) | M3 (Final) | Survey 3 | IN_PROGRESS |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| M1 | Frontend Modularization & Enhancements | Split App.tsx, strict types, zone comparison, weather series, BoundarySketch activation, Vitest tests, clean build | None | DONE |
| M2 | Backend Modularization, ML & Integration Enhancements | Modular APIRouters, state caching/fast startup, spatial clustering, AI regex refinement, optimizer budget limits, adapter test expansion | None | DONE |
| E2E | E2E Testing Track | Design and build comprehensive opaque-box test suite (Tiers 1-4) published via TEST_READY.md | None | DONE |
| M3 | Final E2E Test Pass & Adversarial Hardening | Phase 1: 100% E2E test pass across Tiers 1-4. Phase 2: Tier 5 adversarial coverage hardening | M1, M2, E2E | IN_PROGRESS |

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
  - Request: `OptimizationRequest(zones: list[dict], water_limit: float, budget_limit: float | None = None, budget_enforced: bool = False)`
  - Response: `OptimizationResponse(status: str, total_cooling: float, water_used: float, total_cost: float, budget_limit: float | None, budget_used: float | None, budget_enforced: bool, budget_utilization_pct: float | None, allocations: dict[str, dict[str, float]], sensitivity_50pct_water: dict)`

### 4. Weather & Time-Series Contract
- `GET /api/data/series?city=Ahmedabad`
  - Response: `dict(series: list[dict(timestamp: str, temperature_2m: float, relative_humidity_2m: float, precipitation: float, surface_solar_radiation: float)])`

### 5. AI Assistant Contract
- `POST /api/ai/chat`
  - Request: `ChatRequest(message: str, zone_id: str | None, context: dict | None)`
  - Response: `ChatResponse(response: str, citations: list[str], provider: str)`

---

## Code Layout
- `backend/app/main.py`: FastAPI assembly root (99 SLOC), security middleware, lifecycle, router inclusion
- `backend/app/routes/`: Subdivided APIRouters (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`)
- `backend/app/schemas.py`: Pydantic models with financial budget fields
- `backend/app/services/`: Core logic (`state.py`, `ml.py`, `planning.py`, `data.py`, `sources.py`, `ai.py`)
- `backend/app/db.py`: Database models and connection
- `backend/tests/`: Pytest suite (foundation, pipeline, ai, api, sources, e2e_tiers, challenger_m2, challenger_m2_api_budget)
- `frontend/src/App.tsx`: Clean top-level orchestrator (101 lines, <150 limit)
- `frontend/src/pages/`: Modular page views (`OverviewPage`, `MapPage`, `PredictionsPage`, `ExplainPage`, `RiskPage`, `SimulatorPage`, `OptimizerPage`, `AssistantPage`, `ReportsPage`, `ZoneComparePage`)
- `frontend/src/components/`: Reusable components (`common/`, `layout/`, `map/`, `charts/`, `zone/`, `modals/`)
- `frontend/src/types/`: Strict TypeScript domain interfaces (0 `: any`)
- `frontend/src/services/`: Strongly-typed API client services
- `frontend/src/tests/`: Vitest unit and component tests
