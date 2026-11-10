# Handoff Report: Frontend Type System & Typed Service Layer

**Author:** Explorer M1-2 — Frontend Type System & Service Layer Specialist  
**Working Directory:** `d:\Urban-Heat-Resilience-AI`  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_2`  
**Date:** 2026-11-08  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation

Direct observations from codebase inspection:

1. **Monolithic Untyped API Client:**
   - In `frontend/src/api.ts:1`:
     ```typescript
     export async function api<T = any>(path: string, body?: unknown): Promise<T>
     ```
   - In `frontend/src/App.tsx`, 14 distinct API calls (lines 197, 201, 205, 215, 884, 888, 1023, 1092, 1213, 1217, 1433, 1645, 1789, 1955, 1974) invoke `api(...)` without passing type arguments, resolving to `any`.

2. **Pervasive Component Prop `any` Annotations in `App.tsx`:**
   - Line 148: `function Metric({ label, value, unit, detail, icon: Icon, tone = "green" }: any)`
   - Line 165: `function ZonePicker({ data, selected, onSelect }: any)`
   - Line 545: `function Overview({ overview: o, data, selected, onSelect, layer, onLayer, navigate }: any)`
   - Line 720: `function ZoneTable({ zones, onSelect }: any)`
   - Line 775: `function Importance({ data, local = false }: any)`
   - Line 824: `function ZoneDetails({ selected: p, navigate }: any)`
   - Line 880: `function Prediction({ city, data, overview, notify }: any)`
   - Line 1020: `function Explain({ city, data, selected, onSelect, overview }: any)`
   - Line 1087: `function Risk({ city, data, selected, onSelect }: any)`
   - Line 1203: `function Simulator({ city, data, selected, onSelect, notify }: any)`
   - Line 1426: `function Optimizer({ city, overview, notify }: any)`
   - Line 1639: `function Assistant({ city, data, selected, onSelect }: any)`
   - Line 1786: `function Reports({ city, overview, status, notify }: any)`
   - Line 1943: `function DataDialog({ city, close, notify }: any)`

3. **Untyped Map Component in `frontend/src/components/HeatMap.tsx`:**
   - Lines 46-53:
     ```typescript
     }: {
       data: any;
       layer: string;
       onLayer: (v: string) => void;
       selected: string;
       onSelect: (p: any) => void;
       tall?: boolean;
     })
     ```
   - Line 71: `style={(f: any) => ({ ... })}`

4. **Internal State Typed as `any`:**
   - `App.tsx:1642`: `const [messages, setMessages] = useState<any[]>([]);`
   - `App.tsx:1787`: `const [report, setReport] = useState<any>();`
   - `App.tsx:1959`: `const body: any = { ... };`

5. **Backend Schema Contracts in `backend/app/schemas.py` and `backend/app/main.py`:**
   - `AreaRequest`, `ZoneRequest`, `RiskRequest`, `SimulationRequest`, `OptimizationRequest`, `ChatRequest`
   - `HealthResponse`, `PredictionResponse`, `PredictionBatchResponse`, `ExplanationResponse`, `SimulationResponse`, `OptimizationResponse`, `ChatResponse`
   - 12 ML feature names in `backend/app/services/data.py:13-26`: `ndvi`, `ndwi`, `ndbi`, `ndbai`, `building_density`, `population_density`, `air_temperature`, `humidity`, `rainfall`, `solar_radiation`, `soil_moisture`, `land_cover`.
   - Weather time-series structure in `backend/app/services/sources.py:153-210`: returns daily aggregated points with `date`, `air_temperature_c`, `relative_humidity_pct`, `hours_with_temperature`, `rainfall_mm`, `wind_speed_m_s`, `solar_radiation_mj_m2_day`.

6. **Compiler Strictness:**
   - `frontend/tsconfig.json:12` has `"strict": true`, but because parameters are explicitly typed as `: any`, the compiler allows arbitrary property access without checking.

---

## 2. Logic Chain

1. **Step 1:** From Observation 6, `tsconfig.json` already enforces strict mode (`strict: true`). Therefore, removing `: any` and providing explicit TypeScript definitions will immediately unlock comprehensive compiler verification across the frontend build.
2. **Step 2:** From Observations 1 & 5, the backend endpoints return strictly structured JSON corresponding to Pydantic v2 schemas and deterministic Python dictionaries. Designing corresponding TypeScript interfaces in `frontend/src/types/` (`common.ts`, `geojson.ts`, `ml.ts`, `simulation.ts`, `optimization.ts`, `weather.ts`, `risk.ts`, `chat.ts`, `overview.ts`, `data.ts`) ensures compile-time end-to-end contract parity.
3. **Step 3:** From Observation 1, calling `api("/path")` without explicit typing results in `Promise<any>`, which propagates untyped data into TanStack Query cache (`query.data`) and down through component trees. Replacing `api.ts` with dedicated service modules (`heatService`, `mlService`, `simulationService`, `optimizationService`, `weatherService`, `riskService`, `aiService`, `dataService`, `reportService`) in `frontend/src/services/` ensures that every `useQuery` and `useMutation` hook automatically infers exact return types without manual casts.
4. **Step 4:** From Observations 2, 3, & 4, substituting all `: any` parameter and state annotations with the domain interfaces (`ZoneProperties`, `ZoneFeatureCollection`, `OverviewResponse`, `ModelSummary`, `SimulationResponse`, etc.) closes every type hole in components and hooks.
5. **Step 5:** From Observations 1 & 5, isolating formatters (`fmt`, `label`) and class merge helpers (`cn`) into `frontend/src/lib/utils.ts` and domain constants (`CITIES`, `MAP_LAYERS`, `PAGES`) into `frontend/src/lib/constants.ts` decouples UI formatting from HTTP networking, enabling clean unit testing with Vitest.

---

## 3. Caveats

1. **Backend Route Refactoring (Milestone 2):** In Milestone 2, the backend `main.py` will be modularized into APIRouters in `backend/app/routes/`. The designed frontend service layer calls `/api/*` endpoints which are stable public routes; if route paths are modified during M2, only the service modules will need updates rather than component UI code.
2. **External Data Payload Variations:** Live data ingestion via `/api/data/ingest` returns diverse schemas depending on the source (e.g. Earth Engine vs. OpenAQ vs. OSM vs. Sentinel). The `DataIngestResponse` type union safely handles both structured synthetic responses (`SyntheticSampleIngestResponse`) and broader provider record formats (`Record<string, unknown>`).
3. **Read-Only Investigation Scope:** As an Explorer agent, no source code files in `frontend/src/` were modified. The complete TypeScript code for all types and services has been detailed in `analysis.md` for immediate implementation by the Worker agent.

---

## 4. Conclusion

A complete, strict TypeScript domain model and modular service layer architecture has been designed, fully documented, and aligned with `backend/app/schemas.py`.

The deliverables include:
1. **Strict Types Blueprint (`src/types/`):** 11 dedicated files defining all domain entities (`ZoneProperties`, `ZoneFeature`, `ModelEvaluation`, `TreeSHAPExplanation`, `SimulationResponse`, `OptimizationResponse`, `WeatherSeriesPoint`, `ChatResponse`, `OverviewResponse`, etc.) eliminating all need for `any`.
2. **Modular Service Layer Blueprint (`src/services/`):** 10 strongly-typed service modules wrapping all 24 backend API endpoints with typed error handling via `ApiError`.
3. **Component Prop Specifications:** Exact interfaces for all 14 subcomponents in `App.tsx`, `HeatMap.tsx`, `BoundarySketch.tsx`, and all new pages.
4. **Complete Implementation Roadmap:** Detailed in `analysis.md` ready for immediate execution by the Worker agent in Milestone 1.

---

## 5. Verification Method

To independently verify this design during implementation:

1. **File Inspection:**
   - Read the technical blueprint in `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_2\analysis.md`.
   - Cross-check interface field names against `backend/app/schemas.py` and `backend/app/services/data.py:FEATURES`.

2. **TypeScript Compilation Check:**
   - After the Worker creates `src/types/` and `src/services/` and removes `any` from components:
     ```powershell
     cd d:\Urban-Heat-Resilience-AI\frontend
     npx tsc -b
     ```
   - **Pass condition:** Zero TypeScript diagnostic errors (`exit code 0`).

3. **Production Build Check:**
   - Run Vite production bundle build:
     ```powershell
     cd d:\Urban-Heat-Resilience-AI\frontend
     npm run build
     ```
   - **Pass condition:** Clean build with zero type or bundling errors.

4. **Grepping for `any` Elimination:**
   - Run PowerShell check across frontend source files:
     ```powershell
     cd d:\Urban-Heat-Resilience-AI\frontend
     Select-String -Path src\*.ts, src\*.tsx, src\**\*.ts, src\**\*.tsx -Pattern ": any|\<any\>|any\[\]|as any"
     ```
   - **Pass condition:** Zero matches in application code (excluding third-party libraries).
