# Project: Production-Oriented AI Urban Climate Intelligence, Heat Risk Assessment and Mitigation Planning Platform

## Architecture
- **System Overview**: End-to-end production platform for urban climate resilience, combining Earth Observation raster ingestion, live environmental telemetry, defensible spatial machine learning, multi-criteria heat risk assessment, physical combinatorial optimization, grounded generative AI intelligence, and a dark-first geospatial intelligence frontend.
- **Backend Architecture**: FastAPI asynchronous REST API structured into 9 modular APIRouters (`routes/*`). Decoupled state management in `services/state.py` separating analytical production mode from validated demonstration benchmarks. SQLAlchemy 2.0 ORM with PostgreSQL/PostGIS spatial support and transparent SQLite local fallback. Strict Pydantic v2 schemas (`extra="forbid", allow_inf_nan=False`). Centralized exception handling, structured JSON logging, and in-memory rate limiting.
- **Earth Observation & Ingestion Pipeline**: Landsat 8/9 Collection 2 Level-2 surface temperature rasters (USGS scaling, QA_PIXEL bitmasking, QA_RADSAT saturation filter) via Google Earth Engine with direct STAC/COG fallback; Sentinel-2 Level-2A spectral indices (NDVI, NDWI, NDBI) via Element 84 STAC and AWS S3 WarpedVRT windowing; MODIS 1km LST, ESA WorldCover, NASA SRTM elevation; Open-Meteo weather forecasts and ERA5-Land archives; OpenAQ v3 and CPCB air quality monitoring stations with distance calculation and structured pollutant parsing; CGWB / India-WRIS groundwater observation wells with depth-to-water-table (mbgl) and seasonal trends; polygonal zonal statistics aggregation across municipal wards (Ahmedabad AMC 48 wards benchmark); strict provenance metadata; clean degradation with setup instructions and zero synthetic masquerading.
- **Machine Learning & Spatial XAI**: Spatial and temporal cross-validation avoiding spatial autocorrelation leakage (`validate_no_leakage`); tournament across Random Forest, XGBoost, and LightGBM predicting LST and SUHII relative to rural baseline; comprehensive evaluation via $R^2$, MAE, RMSE, mean prediction bias, residual distribution statistics, and spatial error autocorrelation maps; exact additive TreeSHAP explainability down to $\Delta < 10^{-4}$ with clear non-causal attribution language.
- **Risk Assessment & Physical Optimization**: Multi-factor heat risk framework decomposing Hazard (LST, air temperature, heatwave duration), Exposure (population density, residential density, land use), and Vulnerability (age sensitivity, socioeconomic deprivation, cooling deficit from WorldPop/GHSL and municipal ward data) without substituting population density for vulnerability; literature-grounded cooling simulation with uncertainty ranges; Google OR-Tools CP-SAT discrete combinatorial optimization strictly enforcing physical surface capacities, land-use ceilings, roof mutual exclusivity, and municipal water limits WITHOUT any financial budget constraints or objectives.
- **Grounded AI Assistant**: Multi-provider LLM service (Groq and Google Gemini) with transient retry backoff, context fact grounding, source citations, numeric guardrails, action feasibility checks, and clear user-facing error indicators with setup instructions when providers are unconfigured or unavailable.
- **Frontend Architecture & Geospatial Platform**: React 19 + TypeScript + Vite + Tailwind CSS dark-first climate-intelligence UI system (obsidian `#080c11`, slate `#0e141d`, hairline borders `rgba(255,255,255,0.08)`, monospace telemetry); collapsible application shell (240px expanded / 64px icon-only / mobile drawer) with `Ctrl+K` command palette; 10 canonical page views; reusable Leaflet geospatial mapping system using CartoDB Dark Matter tiles, multi-layer toggle stack (LST, SUHII, NDVI, land cover, AQ/weather/groundwater stations, risk, exposure, proposed interventions), opacity sliders, physical-unit legends, and zone inspection popups.

---

## Feature Inventory

| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | Backend State & Mode Resolution Stabilization | Update `resolve_mode()` in `state.py` to check `HEATWISE_DEMO_MODE=1` when mode is None, clearing 97 test 409 failures | M6 (Backend) | Survey 2 & 3 | DONE |
| 2 | Schemas & Route Parity for Groundwater | Add `"groundwater"` to `AreaRequest.source` enum and wire route handler in `routes/data.py` | M6 (Backend) | Survey 2 | DONE |
| 3 | OR-Tools Solver Windows Stability Guard | Add safe execution wrapper around CP-SAT solver in `optimization.py` to prevent Windows Python 3.14 native crashes | M6 (Backend) & M4 | Survey 2 & 3 | DONE |
| 4 | Structured Logging & Graceful Exceptions | Centralize structured JSON logging and replace unhandled 422s on missing API keys with graceful no-data responses | M6 (Backend) | Survey 2 | DONE |
| 5 | Landsat 8/9 STAC/COG Direct Ingestion | Implement direct Landsat Collection 2 L2 reader via open STAC (Planetary Computer/AWS) with rasterio WarpedVRT when GEE is unconfigured | M1 (Satellite) | Survey 2 | PLANNED |
| 6 | Zonal Statistics Engine across Wards | Implement `calculate_zonal_statistics()` in `geospatial.py` to aggregate raster pixels across municipal ward polygons | M1 (Satellite) | Survey 2 | PLANNED |
| 7 | Elimination of Synthetic Fallback | Replace `synthetic_satellite_fallback()` mock numbers with clean `unavailable` status and setup instructions | M1 (Satellite) | Survey 2 | PLANNED |
| 8 | OpenAQ v3 Station Distance & Pollutant Parsing | Calculate Haversine station distance, parse PM2.5/PM10/NO2/SO2/O3/CO, and format output as `"stations"` array for map layers | M1 (Satellite) | Survey 2 | PLANNED |
| 9 | CGWB / India-WRIS Groundwater Adapter | Ingest Central Ground Water Board monitoring well records (depth in mbgl, trends, coordinates, distance, observation dates) | M1 (Satellite) | Survey 2 | PLANNED |
| 10 | Real-Data Analysis Promotion Bridge | Build service compiling acquired evidence into an `analysis_ready = True` real FeatureCollection for analytical mode | M1 (Satellite) & M6 | Survey 2 | PLANNED |
| 11 | Multi-Factor Heat Risk Decomposition | Expand Hazard (LST + air temp + heatwave duration) and Exposure (population + residential density + land use) in `risk.py` | M2 (Demographics) | Survey 3 | DONE |
| 12 | Indian Ward Demographic Tables | Integrate ward demographic and vulnerability profiles for Ahmedabad, Delhi, and Hyderabad; add raster sampling for WorldPop/GHSL | M2 (Demographics) | Survey 3 | DONE |
| 13 | ML Service Consolidation & Temporal CV | Consolidate `ml.py` and `ml_train.py`, implement temporal validation folds alongside spatial KMeans folds | M3 (ML & XAI) | Survey 3 | DONE |
| 14 | Comprehensive Evaluation Metrics & Spatial Error Maps | Add mean prediction bias, residual distribution statistics, and Moran's I spatial residual autocorrelation mapping | M3 (ML & XAI) | Survey 3 | DONE |
| 15 | Additive TreeSHAP Non-Causal Grounding | Preserve exact additive TreeSHAP explainability while enforcing strict non-causal language in explanations | M3 (ML & XAI) | Survey 3 | DONE |
| 16 | Literature-Grounded Intervention Cooling | Ground intervention cooling rates and water consumption in urban microclimate literature with explicit uncertainty bounds | M4 (Optimization) | Survey 3 | DONE |
| 17 | Physical-Only OR-Tools Combinatorial Optimizer | Strictly enforce surface capacity, land-use, roof exclusivity, and water limits with ZERO financial budget constraints or objectives | M4 (Optimization) | Survey 3 | DONE |
| 18 | Spatial Priority Plan Generation | Generate equity-weighted spatial priority rankings and multi-zone allocation maps from CP-SAT solutions | M4 (Optimization) | Survey 3 | DONE |
| 19 | Grounded AI Assistant Multi-Provider Fallback | Integrate Groq and Google Gemini with transient backoff, fact grounding, citations, and regex numeric guardrails | M5 (Generative AI) | Survey 3 | DONE |
| 20 | AI Provider Downtime User-Facing Error Reporting | Display clear actionable error indicators and setup guidance on provider failure rather than synthetic placeholder text | M5 (Generative AI) | Survey 3 | DONE |
| 21 | Dark-First Climate Intelligence Design System | Transform frontend styling into obsidian/slate palette with monospace telemetry and Linear-level precision | M7 (Frontend) | Survey 1 | DONE |
| 22 | Collapsible Shell & Command Palette | Implement collapsible sidebar (240px / 64px / mobile drawer) and `Ctrl+K` command palette in top command bar | M7 (Frontend) | Survey 1 | DONE |
| 23 | 10 Canonical Page Views | Redesign all 10 views: Overview, Live Map, Heat Analysis, Environmental Analysis (new), Risk, Explainable AI, Simulator, Optimizer, Assistant, Reports | M7 (Frontend) | Survey 1 | DONE |
| 24 | Multi-Layer Geospatial Mapping System | Build Leaflet GIS engine with CartoDB Dark Matter tiles, multi-layer toggle stack, opacity sliders, physical legends, and inspect popups | M7 (Frontend) | Survey 1 | DONE |
| 25 | Comprehensive Regression & E2E Verification | Ensure all 365 backend tests and 91 frontend tests pass with 0 failures, 0 errors, and clean production build | Integration | Survey 1, 2, 3 | PLANNED |

---

## Milestones

| # | Name | Scope & Specialized Agent | Dependencies | Status |
|---|------|---------------------------|-------------|:------:|
| **M0** | Backend Stabilization & Core Architecture | Fix `state.py` mode resolution (clearing 97 test 409s), add groundwater schema/routes, solver Windows guard, structured logging (Agent 6) | None | DONE (25/25 architecture tests pass) |
| **M1** | Earth Observation & Environmental Ingestion | Direct Landsat STAC/COG, zonal statistics engine across wards, OpenAQ distance/parsing fix, CGWB groundwater adapter, eliminate synthetic fallback (Agent 1) | M0 | PLANNED |
| **M2** | Demographics, Vulnerability & Heat Risk | Multi-factor Hazard and Exposure decomposition, Indian ward demographic profiles, WorldPop/GHSL sampling without substituting population for vulnerability (Agent 2) | M0 | DONE (54/54 tests pass) |
| **M3** | Defensible Machine Learning & Spatial XAI | Temporal CV, model tournament, prediction bias, residual stats, spatial error maps, TreeSHAP non-causal explainability, service consolidation (Agent 3) | M0 | DONE (54/54 tests pass) |
| **M4** | Physical Intervention Simulation & Optimization | Literature-grounded cooling mechanisms with uncertainty, OR-Tools CP-SAT physical-only optimization (zero budget constraints), spatial priority plans (Agent 4) | M0 | DONE (32/32 tests pass) |
| **M5** | Grounded Generative AI Assistant | Groq & Gemini multi-provider failover, fact grounding, citations, user-facing error reporting on downtime instead of synthetic responses (Agent 5) | M0 | DONE (48/48 tests pass) |
| **M6** | World-Class Frontend Redesign & Geospatial Map | Complete dark-first redesign, collapsible shell + Ctrl+K command bar, 10 canonical views, multi-layer Leaflet GIS map with physical legends (Agent 7) | M0 | DONE (91/91 tests pass, build clean) |
| **M7** | Integration, E2E Verification & Hardening | Full end-to-end integration, 100% backend (365 tests) and frontend (91+ tests) passing, clean build, and documentation (Orchestrator + All Agents) | M1-M6 | PLANNED |

---

## Interface Contracts

### 1. Spatial Heat & Prediction Contract (`heat.py`, `ml.py`)
- `POST /api/heat/predict`
  - Request: `ZoneRequest(city: str, properties: dict[str, float])`
  - Response: `PredictionResponse(predicted_suhii: float, interval_lower: float, interval_upper: float, confidence: float, model_used: str, base_value: float, contributions: dict[str, float], spatial_error_autocorrelation: float | None = None)`

### 2. Environmental Ingestion & Stations Contract (`sources.py`, `evidence.py`, `routes/data.py`)
- `POST /api/data/ingest`
  - Request: `AreaRequest(city: str, source: Literal["weather", "osm", "satellite", "sentinel2", "monitoring", "groundwater", "copernicus", "worldpop", "ghsl", "nasa_power"], ...)`
  - Response: `IngestResponse(status: str, asset_id: str, count: int, provenance: dict, stations: list[dict] | None = None)`
- Monitoring Station Schema (`air_quality` and `groundwater`):
  - `StationRecord(id: str, name: str, latitude: float, longitude: float, distance_km: float, timestamp: str, measurements: dict[str, float], depth_below_ground_m: float | None = None)`

### 3. Intervention Simulation Contract (`planning.py`, `routes/simulation.py`)
- `POST /api/simulation/run`
  - Request: `SimulationRequest(zone_properties: dict, interventions: dict[str, float])`
  - Response: `SimulationResponse(cooling_celsius: float, uncertainty_range: tuple[float, float], water_m3_day: float, feasible: bool, warnings: list[str], metrics_delta: dict[str, float])`

### 4. Physical Combinatorial Optimization Contract (`optimization.py`, `routes/optimization.py`)
- `POST /api/optimization/run`
  - Request: `OptimizationRequest(zones: list[dict], water_limit: float, min_cooling: float = 0.0)` *(Zero financial budget parameters)*
  - Response: `OptimizationResponse(status: str, total_cooling: float, water_used: float, water_limit: float, allocations: dict[str, dict[str, float]], spatial_priority_ranking: list[str], sensitivity_50pct_water: dict)`

### 5. Multi-Provider Grounded AI Assistant Contract (`ai.py`, `routes/ai.py`)
- `POST /api/ai/chat`
  - Request: `ChatRequest(message: str, zone_id: str | None = None, context: dict | None = None)`
  - Response: `ChatResponse(response: str, citations: list[str], provider: str, status: Literal["ok", "degraded", "error"], error_message: str | None = None)`

### 6. Frontend Navigation & Canonical Routes (`useHashRouter.ts`, `constants.ts`)
- Canonical Route Slugs:
  - `overview`: Overview Command Center
  - `map`: Live Environmental Map
  - `heat`: Heat Analysis (includes zone comparison and LST profiles)
  - `environmental`: Environmental Analysis (weather time series, AQ monitoring, groundwater)
  - `risk`: Heat Risk & Vulnerability
  - `explain`: Explainable AI (TreeSHAP)
  - `simulator`: Mitigation Planning (Intervention Simulation)
  - `optimizer`: Intervention Optimization (Physical CP-SAT)
  - `assistant`: AI Climate Assistant
  - `reports`: Reports & Data Export
  - Backward-compatible aliases: `compare` -> `heat`, `prediction` -> `heat`.

---

## Code Layout

- `backend/app/main.py`: FastAPI root assembly, middleware, security headers, centralized exception handlers
- `backend/app/routes/`: 9 modular APIRouters (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`, `workspace.py`)
- `backend/app/services/`:
  - `state.py`: Thread-safe state store and mode resolution (`resolve_mode`)
  - `satellite.py`: GEE and direct STAC/COG Landsat and Sentinel-2 readers
  - `sources.py`: Open-Meteo, OpenAQ v3, CPCB, and CGWB/India-WRIS adapters
  - `geospatial.py`: Raster reprojection, masking, and ward zonal statistics engine
  - `demographics.py`: WorldPop, GHSL, and Indian municipal ward demographic profiles
  - `risk.py`: Transparent Hazard, Exposure, Vulnerability decomposition
  - `ml.py`: Unified spatial and temporal ML tournament and evaluation
  - `features.py`: Anti-leakage feature definitions and transformations
  - `xai.py`: Exact additive TreeSHAP explainability
  - `planning.py`: Literature-grounded intervention cooling simulation
  - `optimization.py`: Physical-only OR-Tools CP-SAT optimizer and priority ranking
  - `ai.py` & `llm/`: Multi-provider Groq/Gemini assistant with citation grounding
  - `db.py`: Dual PostgreSQL/PostGIS and SQLite database models
  - `migrations.py`: Database schema migrations and PostGIS index management
- `backend/tests/`: Pytest suite (365 tests covering satellite, sources, demographics, ML, XAI, API, optimization, architecture)
- `frontend/src/App.tsx`: Clean top-level orchestrator with collapsible shell
- `frontend/src/components/layout/`: `Sidebar.tsx` (collapsible 240/64/drawer), `Topbar.tsx` with `CommandBar.tsx` (`Ctrl+K`)
- `frontend/src/pages/`: 10 canonical views (`OverviewPage`, `MapPage`, `HeatPage`, `EnvironmentalPage`, `RiskPage`, `ExplainPage`, `SimulatorPage`, `OptimizerPage`, `AssistantPage`, `ReportsPage`)
- `frontend/src/components/map/`: Reusable Leaflet GIS map with dark tiles, multi-layer toggles, opacity sliders, and physical legends
- `frontend/src/services/`: Strongly-typed API client modules (`apiClient.ts`, `dataService.ts`, etc.)
- `frontend/src/types/`: Strict TypeScript domain interfaces
- `frontend/src/tests/`: Vitest test suite (91+ tests)
