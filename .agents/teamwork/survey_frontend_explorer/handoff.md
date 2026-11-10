# Frontend & Testing Survey Report

**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\survey_frontend_explorer\`  
**Date**: 2026-11-09  
**Role**: Frontend, Integration, Testing & Documentation Explorer  

---

## 1. Observation

### 1.1 Frontend Setup & Technology Stack
- **`frontend/package.json`**:
  - `name`: `"heatwise"`, `version`: `"0.1.0"`.
  - Scripts:
    - `"dev"`: `"vite --host 0.0.0.0"`
    - `"build"`: `"tsc -b && vite build"`
    - `"test"`: `"vitest run"`
  - Core dependencies:
    - React 19: `"react": "^19.1.0"`, `"react-dom": "^19.1.0"`
    - State & Data Fetching: `"@tanstack/react-query": "^5.90.0"`
    - Geospatial Mapping: `"leaflet": "^1.9.4"`, `"react-leaflet": "^5.0.0"`, `"@types/leaflet": "^1.9.20"`
    - Data Visualization: `"recharts": "^3.0.0"`
    - UI Components & Utilities: `"@radix-ui/react-slot": "^1.2.3"`, `"class-variance-authority": "^0.7.1"`, `"clsx": "^2.1.1"`, `"tailwind-merge": "^3.3.1"`, `"lucide-react": "^0.468.0"`
    - Styling: `"tailwindcss": "^4.1.0"`, `"@tailwindcss/vite": "^4.1.0"`
  - Dev dependencies:
    - `"typescript": "~5.9.2"`
    - `"vite": "^7.1.0"`
    - `"vitest": "^3.2.0"`
    - `"@vitejs/plugin-react": "^5.0.0"`
- **`frontend/vite.config.ts`**:
  - Line 5: `plugins: [react(), tailwindcss()]`
  - Line 6: `server: { proxy: { "/api": "http://127.0.0.1:8000" } }`
  - Line 7: `build: { chunkSizeWarningLimit: 1000 }`
- **`frontend/tsconfig.json`**:
  - Target: `"ES2022"`, ModuleResolution: `"Bundler"`, Strict: `true`, JSX: `"react-jsx"`, `noEmit: true`.

---

### 1.2 API Service Layer & Endpoint Contracts
- **Facade and Central Client**:
  - `frontend/src/api.ts` provides a unified export:
    - Line 5–11: `api<T>(path, body, options)` calls `request<T>(path, body, options)`.
    - Line 13–15: `download(url, name)` calls `reportService.downloadFile(url, name)`.
    - Line 21: Re-exports all service functions from `./services`.
  - `frontend/src/services/apiClient.ts`:
    - Defines `ApiError` class (lines 1–12) with status, message, and details.
    - Defines `request<T>(path: string, body?: unknown, options?: RequestOptions | AbortSignal)` (lines 20–127).
    - **Line 74**: `response = await fetch("/api" + path, { ... })`.
    - Automatically prepends `"/api"` to every `path` argument passed to `request()`.
    - Supports `AbortSignal`, timeout via `AbortController` (`timeoutMs`), `sessionStorage` bearer token (`heatwise-token`), and robust HTTP/JSON error parsing.
- **Endpoint Path Analysis**:
  - Every service in `frontend/src/services/` invokes `request()` using root-relative paths without `/api`:
    - `heatService.ts`:
      - `getHealth()` -> `request("/health")` -> fetches `/api/health`
      - `getCities()` -> `request("/cities")` -> fetches `/api/cities`
      - `getOverview(city)` -> `request("/overview?city=...")` -> fetches `/api/overview?city=...`
      - `getHeatMap(city)` -> `request("/heat/map?city=...")` -> fetches `/api/heat/map?city=...`
      - `getHotspots(city)` -> `request("/heat/hotspots?city=...")` -> fetches `/api/heat/hotspots?city=...`
      - `predictZone(city, zoneId)` -> `request("/heat/predict", ...)` -> fetches `/api/heat/predict`
    - `mlService.ts`:
      - `getModels(city)` -> `request("/models?city=...")` -> fetches `/api/models?city=...`
      - `trainModels(city)` -> `request("/models/train", ...)` -> fetches `/api/models/train`
      - `getExplanation(city, zoneId)` -> `request("/xai/explain", ...)` -> fetches `/api/xai/explain`
      - `getFeatureImportance(city)` -> `request("/xai/importance?city=...")` -> fetches `/api/xai/importance?city=...`
    - `simulationService.ts`:
      - `getInterventions()` -> `request("/interventions")` -> fetches `/api/interventions`
      - `runSimulation(req)` -> `request("/simulation/run", req)` -> fetches `/api/simulation/run`
      - `getSimulationHistory(city)` -> `request("/simulation/results?city=...")` -> fetches `/api/simulation/results?city=...`
    - `optimizationService.ts`:
      - `runOptimization(req)` -> `request("/optimization/run", req)` -> fetches `/api/optimization/run`
      - `getOptimizationHistory(city)` -> `request("/optimization/results?city=...")` -> fetches `/api/optimization/results?city=...`
    - `weatherService.ts`:
      - `getWeatherSeries()` -> `request("/data/series")` -> fetches `/api/data/series`
    - `riskService.ts`:
      - `analyzeRisk(req)` -> `request("/risk/analyze", req)` -> fetches `/api/risk/analyze`
    - `aiService.ts`:
      - `chat(req)` -> `request("/ai/chat", req)` -> fetches `/api/ai/chat`
    - `dataService.ts`:
      - `getDataStatus()` -> `request("/data/status")` -> fetches `/api/data/status`
      - `getDataRecords(kind)` -> `request("/data/records?kind=...")` -> fetches `/api/data/records?kind=...`
      - `ingestData(req)` -> `request("/data/ingest", req)` -> fetches `/api/data/ingest`
    - `reportService.ts`:
      - `generateReport(city)` -> `request("/reports/generate", { city })` -> fetches `/api/reports/generate`
      - `downloadFile(url, filename)` -> fetches `url` directly with auth headers.
- **Backend Route Mount Comparison**:
  - In `backend/app/main.py`:
    - Line 93: `@app.get("/api/health")`
    - Line 100: `@app.get("/api/tiles/{z}/{x}/{y}.png")`
  - In `backend/app/routes/`:
    - `heat.py` (no router prefix): `@router.get("/api/cities")`, `@router.get("/api/overview")`, `@router.get("/api/heat/map")`, `@router.get("/api/heat/hotspots")`, `@router.post("/api/heat/predict")`.
    - `models.py` (no router prefix): `@router.get("/api/models")`, `@router.post("/api/models/train")`, `@router.post("/api/xai/explain")`, `@router.get("/api/xai/importance")`.
    - `simulation.py` (no router prefix): `@router.get("/api/interventions")`, `@router.post("/api/simulation/run")`, `@router.get("/api/simulation/results")`.
    - `optimization.py`: `prefix="/api/optimization"`, `@router.post("/run")` (`/api/optimization/run`), `@router.get("/results")` (`/api/optimization/results`).
    - `risk.py`: `prefix="/api/risk"`, `@router.post("/analyze")` (`/api/risk/analyze`).
    - `ai.py`: `prefix="/api/ai"`, `@router.post("/chat")` (`/api/ai/chat`).
    - `data.py`: `prefix="/api/data"`, endpoints `/status`, `/records`, `/series`, `/ingest`.
    - `reports.py`: `prefix="/api/reports"`, endpoints `/generate`, `/{id}/download`, `/{id}/csv`, `/{id}/markdown`.
  - **Crucial observation on `/cities` vs `/api/cities`**:
    - The backend does NOT expose a naked `/cities` endpoint; it only exposes `/api/cities`.
    - The frontend services always call `request("/cities")`, which `apiClient.ts` transforms to `fetch("/api/cities")`.
    - Vite's dev proxy forwards `/api` to `http://127.0.0.1:8000`.
    - If a caller erroneously passes `request("/api/cities")`, `apiClient.ts` constructs `"/api/api/cities"`, resulting in a 404 error. The current frontend codebase consistently avoids this double prefix.

---

### 1.3 Inspection of the 10 Dashboard Pages

Navigation is managed via URL hash routing (`frontend/src/hooks/useHashRouter.ts`) with synchronization for active city, zone ID, and map layer (`#/page?city=Ahmedabad&zone=AHM_01&layer=predicted_suhii`).

1. **Overview Page (`frontend/src/pages/OverviewPage.tsx`)**:
   - 4 summary KPI metric cards: Area analyzed (km²), Average surface heat (SUHII °C), Hotspot count (SUHII $\ge 4^\circ\text{C}$), Exposed synthetic population in high-risk zones.
   - Interactive `HeatMap` component with zone selection and layer switcher.
   - Model insight card highlighting top SHAP feature associations.
   - Quick action linking to Simulator.
   - Priority zones `ZoneTable` ranking top 5 vulnerable sectors.
   - Top 5 global feature importance chart (`ImportanceBarChart`).
   - Notice explicitly stating synthetic environmental and demographic data.

2. **Map Page (`frontend/src/pages/MapPage.tsx`)**:
   - Full-height interactive Leaflet map rendering 324 WGS84 zone polygons.
   - 8 switchable map layers: `predicted_suhii`, `risk_score`, `ndvi`, `building_density`, `population_density`, `shap_ndvi`, `shap_ndbi`, `shap_building_density`.
   - `ZoneDetails` side panel synchronized with active zone selection, displaying SUHII confidence interval, LST, NDVI, building density, roof/road percentages, population density, and risk score.

3. **Predictions Page (`frontend/src/pages/PredictionsPage.tsx`)**:
   - Mutation button to retrain spatial models via `mlService.trainModels()`.
   - Comparative evaluation cards for Random Forest, XGBoost, and LightGBM with $R^2$, RMSE, MAE, and validation RMSE.
   - Interactive Recharts `ScatterChart` plotting synthetic labels vs. model predictions for spatial test partition cells.
   - Spatial partition diagram showing train (162), validation (54), buffer (54), and test (54) splits.
   - Uncertainty documentation: validation residual empirical band ($\pm 0.90^\circ\text{C}$).
   - Integrated `WeatherTimeSeriesChart` displaying meteorological observations.

4. **Explain Page (`frontend/src/pages/ExplainPage.tsx`)**:
   - Zone picker selector.
   - Global feature importance Recharts bar chart from `overview.importance`.
   - Local zone TreeSHAP contribution chart showing feature-level shifts with exact additivity: $\text{Base Value} + \sum \text{SHAP} = \text{Prediction}$.
   - Spatial SHAP Leaflet map (`shap_ndvi`) illustrating geographic variation in vegetation influence.
   - Explicit scientific caveat notice that SHAP reflects statistical model associations, not causal cooling coefficients.

5. **Risk Page (`frontend/src/pages/RiskPage.tsx`)**:
   - Multi-criteria risk formulation: $\text{Risk} = \text{Hazard}^{w_H} \times \text{Exposure}^{w_E} \times \text{Vulnerability}^{w_V} \times 100$.
   - Interactive range sliders for $w_H, w_E, w_V$ (0.1 to 3.0).
   - Recalculate mutation calling `riskService.analyzeRisk()`.
   - Explicit documentation on component normalization:
     - Hazard: SUHII / $8^\circ\text{C}$
     - Exposure: Population density / 25,000 people/km²
     - Vulnerability: Synthetic elderly share / 25%
   - Searchable priority `ZoneTable` with risk level badges (High, Moderate, Low).

6. **Simulator Page (`frontend/src/pages/SimulatorPage.tsx`)**:
   - 8 intervention coverage sliders: Urban tree canopy, Pocket parks & bioswales, Large public green space, Cool roofs, Permeable/reflective pavements, Green corridors, Rooftop intensive gardens, Fountains & retention ponds.
   - Physical quota displays: Available unbuilt ground %, Roof area %, Road area %.
   - Water limit input (m³/day).
   - Simulation mutation calling `simulationService.runSimulation()`.
   - Feasibility check: displays cooling impact with $\pm 40\%$ sensitivity range, or lists exact physical constraint violations if infeasible.
   - Scenario comparison table of previously saved simulation runs.

7. **Optimizer Page (`frontend/src/pages/OptimizerPage.tsx`) — Budget Analysis**:
   - Subtitle explicitly declares: `"OR-Tools CP-SAT · no budget objective"` (line 43).
   - Form controls (lines 45–120) currently only provide inputs for:
     - Total available water (m³/day)
     - Maximum added vegetation (%)
     - Use of available ground area (%)
     - Minimum mean surface cooling (°C)
   - Mutation payload in `run.mutate()` (lines 28–34) only transmits `city`, `water_limit`, `max_vegetation_pct`, `land_limit_pct`, and `min_cooling`.
   - **Key Finding**: In `frontend/src/types/optimization.ts`, the TypeScript definitions already declare:
     - `OptimizationRequest.budget_limit?: number`
     - `OptimizationRequest.budget_enforced?: boolean`
     - `OptimizationResponse.total_cost?: number`
     - `OptimizationResponse.budget_limit?: number | null`
     - `OptimizationResponse.budget_used?: number | null`
     - `OptimizationResponse.budget_enforced?: boolean`
     - `OptimizationResponse.budget_utilization_pct?: number | null`
   - In `backend/app/services/planning.py`, the OR-Tools CP-SAT solver already enforces CapEx financial budget constraints (`model.Add(sum(cost_terms) <= int(budget_limit))`) and computes `budget_used` and `budget_utilization_pct`.
   - **Gap**: The UI in `OptimizerPage.tsx` does NOT yet render budget limit inputs or enforcement checkboxes, nor does it display total cost or budget utilization in the result cards or allocation table.

8. **Assistant Page (`frontend/src/pages/AssistantPage.tsx`) — Groq/Gemini Interface**:
   - Provider selection dropdown with 4 options:
     1. `"auto"`: "Auto · Groq → Gemini"
     2. `"groq"`: "Groq"
     3. `"gemini"`: "Gemini"
     4. `"local"`: "Local evidence summary"
   - Calls `aiService.chat({ city, zone_id, message, provider })`.
   - Renders assistant response with:
     - Active provider name and fallback badge ("Template fallback" vs "Provider response").
     - High-level summary text.
     - Structured findings with inline evidence citations (`fact_ids`, e.g., `[heat_map_ahmedabad, tree_shap_xgb]`).
     - Actionable intervention badges.
     - Collapsible `<details>` section for "Evidence & limitations": predicted SUHII (tagged synthetic), analytical limitations, and provider error/failure diagnostics (`failure.provider: failure.reason`).
     - ZoneDetails sidebar.

9. **Reports Page (`frontend/src/pages/ReportsPage.tsx`)**:
   - Banner with `"SYNTHETIC DEMONSTRATION"` badge.
   - Generation mutation calling `reportService.generateReport()`.
   - Direct download buttons for Markdown (`.md`), CSV (`.csv`), and full JSON (`.json`) analysis snapshots via `reportService.downloadFile()`.
   - Methodology & provenance card documenting SUHII definitions, synthetic grid parameters, 3 tree ensemble models, spatial splitting, and CP-SAT formulation.
   - Connection status indicators displaying live configuration state for Database, Groq, Google Gemini, and Google Earth Engine.

10. **Zone Compare Page (`frontend/src/pages/ZoneComparePage.tsx`)**:
    - Multi-zone differential selector allowing up to 4 concurrent zones.
    - Quick-select shortcut buttons: "Top 3 Hotspots" and "Extreme Contrast".
    - Disparity summary cards:
      - Thermal Disparity ($\Delta\text{SUHII}$ in °C between hottest and coolest selected zone).
      - Combined Exposed Population across selected zones.
      - Maximum Theoretical Cooling Potential (°C).
    - Recharts `ZoneComparisonChart` bar chart comparing SUHII, LST, vegetation, building density, and risk score across selected zones.
    - Comprehensive side-by-side comparison table grouped into:
      - Thermal Profile & LST (SUHII, LST, 95% Confidence Interval).
      - Vegetation & Built-up Density (NDVI, NDBI, Building Density).
      - Demographics & Vulnerability (Population, Elderly Share 65+, Risk Score & Level).
      - Intervention Capacity & Physical Constraints (Unbuilt Ground %, Roof %, Max Cooling Potential).
      - Direct action buttons linking to Simulator and Explainable AI for each compared zone.

---

### 1.4 Data Transparency & Synthetic Data Labels
Pervasive labeling is embedded across the frontend UI:
- **`Sidebar.tsx`** (line 56): `"Demonstration research prototype. Synthetic data for preview."`
- **`HeatMap.tsx`** (line 119): `"1 km grid · Synthetic"`
- **`OverviewPage.tsx`**:
  - Line 77: `"Synthetic population · priority proxy"`
  - Line 107: `"Illustrative grid · WGS84"`
  - Line 206: `"Model associations, not proof of causation."`
  - Lines 215–219: `<Notice>` banner stating synthetic environmental and demographic data.
- **`PredictionsPage.tsx`**:
  - Lines 61–64: `<Notice>` banner: `"All metrics below are measured on held-out synthetic labels. Real-world validation is unavailable."`
  - Line 115: `subtitle="Spatial test partition only · synthetic SUHII"`
  - Line 123: X-axis label `"Synthetic label"`
  - Line 172: `"Uncertainty: ±...°C from the validation set's 90th-percentile absolute residual. This is an empirical band; real-world coverage is unknown."`
- **`ExplainPage.tsx`** (lines 94–97): Notice that SHAP explains associations and is not used as cooling coefficients.
- **`RiskPage.tsx`** (lines 121–125): Notice that socioeconomic and clinical health data are unavailable, serving only as a screening proxy.
- **`SimulatorPage.tsx`** (lines 67–70): Notice specifying hypothetical cooling estimates and uncalibrated coefficients with $\pm 40\%$ sensitivity.
- **`OptimizerPage.tsx`** (lines 230–234): Notice clarifying population in selected zones is a planning proxy, not people protected.
- **`AssistantPage.tsx`**:
  - Line 140: `"Predicted SUHII: ...°C · synthetic."`
  - Line 190: `"Evidence-grounded support. Verify recommendations before making planning decisions."`
- **`ReportsPage.tsx`**:
  - Line 71: `<Badge>SYNTHETIC DEMONSTRATION</Badge>`
  - Line 130: `"reference: ...°C, synthetic."`
  - Line 134: `"The acquisition date is a demonstration label. Live imports never silently replace the sample."`
- **`DataDialog.tsx`**:
  - Line 78: `"Live evidence stays separate from synthetic predictions."`
  - Line 293: Clear label distinguishing `"Live source"` vs. `"Synthetic sample"`.
  - Line 313: Catalog status indicating `"Live configured"` vs. `"Synthetic mode"`.
- **`WeatherTimeSeriesChart.tsx`** (lines 189–191): Explicit notice distinguishing station air temperature (2 m atmospheric measurement, non-synthetic) from satellite LST and SUHII.

---

### 1.5 Frontend & E2E Testing Verification
- **Test Runner**: Vitest v3.2.7 configured via `frontend/package.json` (`"test": "vitest run"`).
- **Execution of Vitest Suite** (`cd frontend; npm run test`):
  - Result: **6 test files passed, 54 tests passed** in 3.07s.
  - Test inventory:
    1. `src/tests/zoneCompare.test.ts` (6 tests): Selection cap (max 4), minimum 1 retained, toggle logic, metric deltas, disparity sorting.
    2. `src/tests/integration_challenge.test.ts` (18 tests): URL hash parsing, plural aliases, query persistence across city switches, state synchronization, timeout controller, aborted requests, network drop simulation, HTML error handling.
    3. `src/tests/metrics.test.ts` (11 tests): SUHII calculation, risk thresholds (High/Moderate/Low), theoretical cooling potential capping (max 3.0°C), physical capacity constraint validation.
    4. `src/tests/weather.test.ts` (3 tests): Temperature extremes, mean humidity ignoring null records, empty series resilience.
    5. `src/tests/button.test.tsx` (5 tests): Server-side static HTML rendering for button primitives and variants.
    6. `src/tests/api.test.ts` (11 tests): `fmt()` Indian locale number formatting, `label()` spatial keys, GET/POST request generation, auth header attachment, `ApiError` propagation.
- **Production Build Verification** (`cd frontend; npm run build`):
  - Executed `tsc -b && vite build`.
  - Result: **0 TypeScript errors, build succeeded** in 23.24s.
  - Chunks generated:
    - `dist/index.html`: 0.53 kB
    - `dist/assets/index-DDkCALQo.js`: 954.86 kB (gzip: 283.51 kB)
    - `dist/assets/index-eINQ-3y0.css`: 62.63 kB (gzip: 17.67 kB)
    - Fonts: `manrope` (164.70 kB), `dm-sans` (240.16 kB)
- **E2E Browser Test Script**:
  - File: `scripts/browser_smoke.py` (63 lines).
  - Uses Playwright Chromium in headless mode against `http://127.0.0.1:8000`.
  - Validates 324 interactive Leaflet cells, tab transitions across 7 views, risk recalculation, simulation execution, CP-SAT optimization, AI assistant local fallback, report CSV download, multi-city switching (Delhi/Ahmedabad), and mobile viewport (390×844) responsiveness without horizontal overflow.

---

### 1.6 Documentation Review
- **`README.md`** (259 lines):
  - Accurately details project mission, local setup instructions (Python 3.12+, Node 22+, npm), SQLite and Docker PostGIS startup, Vite dev proxy, and build commands.
  - Full structural listing of 10 frontend view pages, modular API services, and backend routers.
  - Data integration status table documenting live verification for Open-Meteo, Sentinel-2 STAC, and COGs, alongside credentialed prerequisites for Earth Engine.
  - Comprehensive model metrics table ($R^2$, RMSE, MAE) and clear disclaimer that metrics are computed on synthetic spatial test partitions.
- **`docs/`**:
  - `docs/METHODOLOGY.md` (8,146 bytes): Detailed documentation of spatial partitioning, ML algorithms, TreeSHAP, parametric risk equations, intervention physics, and CP-SAT objective functions.
  - `docs/VERIFICATION.md` (8,391 bytes): Records executed verification checks and limitations.
- **`TEST_INFRA.md` & `TEST_READY.md`**:
  - Comprehensive documentation of testing tiers (Tiers 1–4), fast-startup environment flags, and mock boundaries.

---

## 2. Logic Chain

1. **Premise**: The frontend must reliably proxy and consume all backend API endpoints without path collisions or 404 errors.
   - *Observation*: `apiClient.ts:74` unconditionally prepends `"/api"` (`fetch("/api" + path)`).
   - *Observation*: All frontend services pass paths without `/api` (e.g. `request("/cities")`), producing requests to `/api/cities`.
   - *Observation*: All backend routes in `backend/app/routes/` and `main.py` are explicitly declared under `/api` (`@router.get("/api/cities")`, `APIRouter(prefix="/api/optimization")`).
   - *Deduction*: Frontend and backend endpoint contracts are perfectly aligned. There is no route mismatch or double-prefixing.

2. **Premise**: The user requested verification of how budget is currently displayed and requested in the Optimizer page.
   - *Observation*: In `frontend/src/types/optimization.ts`, `budget_limit`, `budget_enforced`, `total_cost`, and `budget_utilization_pct` are fully defined.
   - *Observation*: In `backend/app/routes/optimization.py` and `services/planning.py`, OR-Tools CP-SAT implements budget enforcement and returns cost utilization.
   - *Observation*: In `frontend/src/pages/OptimizerPage.tsx`, the subtitle is `"OR-Tools CP-SAT · no budget objective"`, form inputs for budget are absent, and the mutation does not pass budget parameters.
   - *Deduction*: Budget optimization is supported in backend schemas, services, and frontend TypeScript type definitions, but is omitted from the frontend UI interface in `OptimizerPage.tsx`.

3. **Premise**: The frontend must strictly uphold data transparency, distinguishing synthetic demonstration data from live observations.
   - *Observation*: Prominent `<Notice>` banners, metric card details, and chart subtitles across all 10 pages, sidebar, map, and modals explicitly flag synthetic data, model limitations, and proxy assumptions.
   - *Observation*: `DataDialog.tsx` explicitly marks retrieved data as `"Live source"` vs. `"Synthetic sample"`.
   - *Deduction*: Data transparency is comprehensively implemented throughout the UI.

4. **Premise**: The frontend codebase must be buildable, type-safe, and verifiable by automated tests.
   - *Observation*: `vitest run` passed 54/54 tests across 6 suites with zero failures.
   - *Observation*: `tsc -b && vite build` compiled the entire production bundle with zero TypeScript diagnostics.
   - *Deduction*: The frontend is in a healthy, regression-free, and production-ready state.

---

## 3. Caveats

1. **Live Browser Smoke Execution**: Playwright browser smoke test (`scripts/browser_smoke.py`) requires a running FastAPI backend server on port 8000 and an installed Chromium binary. During this survey phase, static unit and integration test suites (`vitest`) and compiler checks (`tsc -b && vite build`) were executed directly, but `browser_smoke.py` was inspected rather than run against a live daemon.
2. **Missing Budget Controls in Optimizer UI**: While the backend solver and TypeScript types support budget caps, the UI controls in `OptimizerPage.tsx` do not expose them. Adding budget inputs (e.g., CapEx slider and budget enforcement toggle) is an implementation task for subsequent phases.
3. **External Real Labeled Data**: As documented across the application, all spatial predictions, demographics, and intervention impacts operate on synthetic baseline grids. The UI does not currently feature live model calibration against external observed ground-truth datasets.

---

## 4. Conclusion

1. **Architecture & Health**: The Heatwise frontend is a well-structured, modular React 19 / TypeScript / Vite application with 10 fully implemented dashboard pages, robust hash routing, TanStack Query state caching, and responsive styling.
2. **Endpoint Alignment**: API communication is unified through `apiClient.ts` (`fetch("/api" + path)`), correctly matching backend `/api` routes without path discrepancies.
3. **UI Completeness & Identified Gap**: All 10 pages (Overview, Map, Predictions, Explain, Risk, Simulator, Optimizer, Assistant, Reports, Zone Compare) are fully functional. In the Optimizer page, budget constraint inputs and cost displays are currently absent in the UI despite full backend and schema support.
4. **Data Transparency**: Strict labeling of synthetic data vs. live observations is present across all pages, notices, charts, and dialogues.
5. **Testing & Build**: The Vitest suite (54 tests) and production Vite build pass with zero errors.

---

## 5. Verification Method

To independently verify these findings, execute the following commands in PowerShell from the project root:

1. **Run Frontend Vitest Suite**:
   ```powershell
   cd frontend
   npm run test
   ```
   *Expected outcome*: 6 test files passed, 54 passed.

2. **Run TypeScript Compiler & Vite Production Build**:
   ```powershell
   cd frontend
   npm run build
   ```
   *Expected outcome*: Zero errors; output files written to `frontend/dist/`.

3. **Verify API Endpoint Alignment**:
   Inspect `frontend/src/services/apiClient.ts` (line 74: `fetch("/api" + path)`) and check route declarations in `backend/app/routes/` to confirm all backend routes use the `/api` prefix.

4. **Verify Optimizer Budget Gap**:
   Inspect `frontend/src/pages/OptimizerPage.tsx` lines 26–36 and line 43 against `frontend/src/types/optimization.ts` lines 4–13.

5. **Invalidation Conditions**:
   - Failure of any of the 54 Vitest tests.
   - TypeScript compilation errors during `npm run build`.
   - Discovery of any direct frontend fetch call using `/api/api/...` or an unproxied naked path like `/cities` without the `/api` prefix on the backend.
