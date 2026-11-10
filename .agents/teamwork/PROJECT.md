# Project: Heatwise AI Urban Heat Resilience Platform

## Architecture
Heatwise is an AI-powered urban heat prediction, resilience, and mitigation platform.
The architecture consists of:
- **FastAPI Backend (`backend/app/`)**:
  - `main.py`: Application lifespan, middleware, router registration, static asset mounting, direct aliases (`/cities`, `/overview`, `/health`), and `/api/api` transparent normalization.
  - `db.py`: Hybrid SQLite & PostgreSQL/PostGIS ORM with polymorphic `Record` and spatial `Zone` models, 30s timeout, safe extension initialization.
  - `routes/`: Modularized API endpoints (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`) with unified `prefix="/api/..."` declarations.
  - `services/`:
    - `sources.py`, `geospatial.py`, `satellite.py`: Real remote sensing ingestion (Landsat 8/9 LST, Sentinel-2 SCL indices, MODIS MOD11A2) with synthetic fallback.
    - `demographics.py`, `risk.py`: Demographic data (WorldPop, GHSL, Census of India ward registry) and IPCC AR5/AR6 Hazard × Exposure × Vulnerability framework with strict weight validation.
    - `features.py`, `ml.py`, `xai.py`: 3-model tournament (RF, XGBoost, LightGBM) with 6-block spatial separation, buffer fold (Block 4), exact additive TreeSHAP explainability, and cross-zone heat differential attribution.
    - `planning.py`, `optimization.py`: 8 cooling intervention models with physical constraints, saturation, and Google OR-Tools CP-SAT discrete optimization (financial budget constraints completely removed).
    - `ai.py`, `llm/`: Groq and Gemini decision support with strict TreeSHAP grounding, numeric regex guardrails (`NUMERIC_MEASUREMENT_PATTERN`), domain whitelist, action feasibility validation, and local fallback.
    - `state.py`: Thread-safe caching and pipeline orchestration.
  - `schemas/`: Pydantic v2 request and response contracts (`schemas.py`, `schemas/ai.py`).
- **React / Vite / TypeScript Frontend (`frontend/src/`)**:
  - 10 Dashboard Views: Overview, Map, Compare, Predictions, Explain, Risk, Simulator, Optimizer, Assistant, Reports.
  - Centralized API Client (`services/apiClient.ts`) calling `/api/*`.
  - Pervasive data transparency and synthetic data indicator banners.

---

## Feature Inventory

| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | API Route Consistency | Harmonize router declarations across all routes to prevent `/api/api` and ensure clean API contracts | M6 (Backend Architecture) | Survey / Prompt | DONE |
| 2 | Risk Module Modularization | Extract `risk()` from `planning.py` to `backend/app/services/risk.py` with backward-compatible re-exports | M6 & M2 | Survey / Prompt | DONE |
| 3 | Database & Schema Reliability | Verify SQLite and PostGIS connection handling, model schemas, and error responses | M6 (Backend Architecture) | Survey / Prompt | DONE |
| 4 | Real Landsat LST Ingestion | Google Earth Engine Landsat 8/9 Collection 2 L2 thermal LST ingestion with QA_PIXEL / QA_RADSAT masking | M1 (Satellite EO) | Survey / Prompt | DONE |
| 5 | Sentinel-2 Optical Indices | Sentinel-2 L2A ingestion (GEE and AWS Element 84 COG with WarpedVRT to EPSG:6933 at 100m) with SCL filtering and NDVI, NDWI, NDBI calculation | M1 (Satellite EO) | Survey / Prompt | DONE |
| 6 | MODIS MOD11A2 & SUHII Calculation | Supplementary MODIS LST and calculation of SUHII = Urban LST - Rural Reference LST with metadata | M1 (Satellite EO) | Survey / Prompt | DONE |
| 7 | Labelled Synthetic Fallback | Maintain clearly labelled synthetic demonstration fallback with provenance metadata when live feeds fail or lack credentials | M1 (Satellite EO) | Survey / Prompt | DONE |
| 8 | Demographic Data Ingestion | Integrate WorldPop and GHSL population datasets and structure for Census of India data | M2 (Demographics) | Survey / Prompt | DONE |
| 9 | IPCC Heat-Risk Framework | Implement Heat Risk = Hazard × Exposure × Vulnerability with configurable normalization and weights | M2 (Demographics & Risk) | Survey / Prompt | DONE |
| 10 | Zone-Level Demographic Features | Join population, age distribution (elderly share), and built-up density to geographical analysis zones without inventing values | M2 (Demographics & Risk) | Survey / Prompt | DONE |
| 11 | Spatial Cross-Validation & Anti-Leakage | 6-block spatial separation with explicit spatial buffer fold (Block 4) to eliminate autocorrelation data leakage | M3 (ML & XAI) | Survey / Prompt | DONE |
| 12 | ML Model Tournament & Persistence | Automated competitive tournament across Random Forest, XGBoost, and LightGBM with lowest validation RMSE selection, model saving/loading | M3 (ML & XAI) | Survey / Prompt | DONE |
| 13 | Exact Additive TreeSHAP & Spatial XAI | Exact TreeSHAP local explanations per zone (base + sum = pred), global feature ranking, and geographic contribution visualization | M3 (ML & XAI) | Survey / Prompt | DONE |
| 14 | Model Validation Separation | Rigorous separation of synthetic benchmark performance metrics from real-world observation metrics | M3 (ML & XAI) | Survey / Prompt | DONE |
| 15 | 8 Cooling Intervention Models | Tree planting, vegetation expansion, urban parks, cool roofs, reflective pavements, green corridors, rooftop gardens, water-based cooling with physical parameters | M4 (Simulation & Optimization) | Survey / Prompt | DONE |
| 16 | Removal of Financial Budget Constraints | Completely remove budget_limit, budget_enforced, financial optimization constraints, and budget-related input fields; retain physical constraints | M4 (Simulation & Optimization) | Task Directive | DONE |
| 17 | OR-Tools CP-SAT Discrete Optimization | Maximize equity-weighted heat risk reduction and population protected under physical land, water, exclusivity, and 3.0°C cooling limits | M4 (Simulation & Optimization) | Survey / Prompt | DONE |
| 18 | Infeasibility Explanations & Alternatives | Generate explicit physical conflict explanations and alternative scenarios (e.g. half-water scenario) | M4 (Simulation & Optimization) | Survey / Prompt | DONE |
| 19 | Groq & Gemini Decision Support | Provider abstraction for Groq API and Google Gemini API with model discovery, retries, and rate-limit handling | M5 (GenAI Layer) | Survey / Prompt | DONE |
| 20 | Strict LLM Fact Grounding & Numeric Guardrails | Regex numeric measurement audit against actual ML, risk, and simulation facts to prevent hallucinated numbers; local evidence summary fallback | M5 (GenAI Layer) | Survey / Prompt | DONE |
| 21 | Dashboard Integration & UI Updates | Maintain all 10 dashboard pages (Overview, Map, Predictions, Explain, Risk, Simulator, Optimizer, Assistant, Reports, Zone Compare) matching backend contracts | M7 (Frontend & Docs) | Survey / Prompt | IN_PROGRESS |
| 22 | Data Transparency & Synthetic Banners | Prominent labels: "Demonstration data — not a validated real-world observation" and source metadata across UI | M7 (Frontend & Docs) | Survey / Prompt | IN_PROGRESS |
| 23 | Comprehensive Testing & Build | 100% pass on backend pytest (355+ tests), frontend vitest (54+ tests), TypeScript compilation, and production Vite build | M8 (E2E Testing & Final Verification) | Survey / Prompt | PLANNED |
| 24 | Complete Documentation | Update README.md, docs/METHODOLOGY.md, docs/VERIFICATION.md with local setup, dataset provenance, and verification evidence | M7 & M8 | Survey / Prompt | IN_PROGRESS |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Satellite Data & Earth Observation | Modularize `satellite.py` and `geospatial.py`, enhance Landsat 8/9 LST, Sentinel-2 SCL indices, MODIS LST, SUHII calculation, metadata, and labeled synthetic fallback | none | DONE |
| M2 | Demographic Data & Vulnerability | Create `demographics.py` and `risk.py`, integrate WorldPop/GHSL population joins, implement IPCC AR5/AR6 Hazard × Exposure × Vulnerability framework | none | DONE |
| M3 | Machine Learning & Spatial XAI | Modularize `features.py` and `xai.py`, maintain 6-block spatial separation with buffer fold, model tournament (RF, XGB, LGBM), exact TreeSHAP, separate real vs synthetic metrics | M1, M2 | DONE |
| M4 | Intervention Simulation & Optimization | Modularize `optimization.py`, implement 8 interventions, delete financial budget constraints, optimize equity-weighted cooling with OR-Tools CP-SAT | M2, M3 | DONE |
| M5 | Groq & Gemini GenAI Layer | Structure `services/llm/` and `schemas/ai.py`, Groq/Gemini client abstraction, TreeSHAP fact grounding, numeric measurement regex audit, local fallback | M3, M4 | DONE |
| M6 | Backend Architecture, API & DB | Harmonize router prefixes across `routes/`, integrate `services/risk.py`, verify SQLite/PostGIS database config, ensure configuration robustness | none | DONE |
| M7 | Frontend Integration & Documentation | Update Optimizer page (reflect budget removal), verify all 10 pages, ensure synthetic data warnings, update README.md, METHODOLOGY.md, VERIFICATION.md | M4, M5, M6 | IN_PROGRESS |
| M8 | Full Regression & Verification | Run all backend pytest suites, frontend Vitest suites, Vite production build, end-to-end integration verification | M1-M7 | PLANNED |

---

## Interface Contracts

### 1. `backend/app/services/risk.py` ↔ Consumers (`planning.py`, `state.py`, `routes/risk.py`)
- `def risk(p: dict, weights: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> dict`:
  - Inputs: `p` containing `predicted_suhii` (or `observed_suhii`), `population_density`, `elderly_share`.
  - Outputs: `{"risk_score": float, "hazard": float, "exposure": float, "vulnerability": float, "risk_level": "High" | "Moderate" | "Low", "missing_indicators": list[str], "method": str, "synthetic_demographics": bool}`.
  - Re-exported in `backend/app/services/planning.py` for backward compatibility.

### 2. `backend/app/services/optimization.py` ↔ Routes & Planning
- `def optimize(zones: list[dict], min_cooling: float = 0.5, water_limit: float = 50000.0, land_limit_pct: float = 50.0, max_vegetation_pct: float = 40.0) -> dict`:
  - Note: Financial `budget_limit` and `budget_enforced` parameters completely removed from CP-SAT solver constraints.
  - Outputs: `{"status": str, "feasible": bool, "mean_cooling": float, "selections": list[dict], "total_water_used": float, "violations": list[str], "alternative": dict}`.

### 3. API Router Standardization
- All endpoints served under `/api/*`:
  - Direct aliases for `/cities`, `/overview`, `/health`.
  - Transparent ASGI normalization for `/api/api/*`.
