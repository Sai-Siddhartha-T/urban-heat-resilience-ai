# Comprehensive Survey Report: Frontend Architecture & UI/UX

**Author:** Explorer 1 — Frontend Architecture & UI/UX Specialist  
**Date:** 2026-11-08  
**Project:** Heatwise — AI-Powered Urban Heat Resilience & Mitigation Platform (`frontend/`)  
**Target Codebase:** `frontend/src/App.tsx`, `package.json`, `vite.config.ts`, `tsconfig.json`, `styles.css`, and associated components.

---

## 1. Executive Summary

A comprehensive architectural and code-level investigation of `frontend/` was conducted. The frontend application is built with **React 19.1.0**, **Vite 7.1.0**, **Tailwind CSS 4.1.0**, **@tanstack/react-query 5.90.0**, **Leaflet 1.9.4 / react-leaflet 5.0.0**, and **Recharts 3.0.0**.

### Key Findings:
1. **Severe Monolith (`App.tsx` = 2,164 lines):** The entire application logic, 14 subcomponents, navigation, forms, modals, tables, charts, and state are packed into a single file (`frontend/src/App.tsx`).
2. **Untyped Codebase & Widespread `any`:** `api.ts` defines `api<T = any>`, and virtually all component props and callbacks in `App.tsx` and `HeatMap.tsx` are typed as `any`. No shared TypeScript interfaces exist for zones, GeoJSON features, ML models, simulations, or risk calculations.
3. **Dead Code & Abandoned Components:**
   - `frontend/src/components/BoundarySketch.tsx` (117 lines) is imported on line 58 of `App.tsx` but never rendered anywhere in the application. In `DataDialog`, users are instead presented with a raw `<textarea>` to manually paste GeoJSON.
   - Recharts `LineChart` and `Line` are imported (lines 53-54) but unused.
   - In `Prediction` (lines 882-886), `/data/series` is queried and `meteorology = series.data?.series?.[0]` is extracted, but never rendered anywhere.
   - Unused Lucide icons: `BarChart3`, `CloudSun`, `MessageSquare`, `Zap`.
4. **Missing Features Highlighted in Prompt:**
   - **Zone Comparison:** No capability exists to select, compare, or contrast multiple zones side-by-side on thermal, vegetation, vulnerability, or constraint metrics.
   - **Weather Time-Series Integration:** Open-Meteo hourly weather series data returned by `/data/series` is not visualized.
5. **Testing Failure:**
   - `npm test` (`vitest run`) fails immediately with exit code 1 (`No test files found, exiting with code 1`). Zero unit or component tests exist.
6. **Build Status:**
   - `npm run build` (`tsc -b && vite build`) succeeds in 20.90s, but bundles everything into a single massive `902.32 kB` JS file without chunk splitting, relying on `chunkSizeWarningLimit: 1000` in `vite.config.ts`.

---

## 2. Directory Structure & Build Configuration

### 2.1 File Tree
```
frontend/
├── dist/                          # Production build output
├── index.html                     # HTML entry point (title: "Heatwise — Urban Heat Intelligence")
├── package.json                   # Dependencies & scripts
├── package-lock.json
├── tsconfig.json                  # TypeScript bundler mode config
├── tsconfig.tsbuildinfo
├── vite.config.ts                 # Vite config with React, Tailwind, and /api proxy
└── src/
    ├── api.ts                     # Fetch client wrapper, download, fmt, label (55 lines)
    ├── App.tsx                    # Monolithic application file (2,164 lines)
    ├── main.tsx                   # React root & QueryClientProvider setup (17 lines)
    ├── styles.css                 # 2,372 lines of custom CSS + Tailwind v4 import
    ├── assets/
    │   ├── dm-sans.ttf / dm-sans-OFL.txt
    │   └── manrope.ttf / manrope-OFL.txt
    └── components/
        ├── BoundarySketch.tsx     # Leaflet polygon click sketcher (117 lines, UNUSED)
        ├── button.tsx             # Radix Slot button primitive + cn helper (29 lines)
        └── HeatMap.tsx            # Leaflet map with GeoJSON and layers (140 lines)
```

### 2.2 Dependencies (`package.json`)
```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.90.0",
    "@radix-ui/react-slot": "^1.2.3",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.3.1",
    "leaflet": "^1.9.4",
    "lucide-react": "^0.468.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-leaflet": "^5.0.0",
    "recharts": "^3.0.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.20",
    "@types/react": "^19.1.0",
    "@types/react-dom": "^19.1.0",
    "@vitejs/plugin-react": "^5.0.0",
    "typescript": "~5.9.2",
    "vite": "^7.1.0",
    "vitest": "^3.2.0",
    "tailwindcss": "^4.1.0",
    "@tailwindcss/vite": "^4.1.0"
  }
}
```

### 2.3 Build & Test Verification Commands & Outputs
- **Build Command:** `cd frontend; npm run build`
  - Output: `tsc -b && vite build`
  - Result: Exit code 0, 2,062 modules transformed in 20.90s.
  - Chunks generated:
    - `dist/index.html` (0.53 kB)
    - `dist/assets/index-ChXogCZA.css` (51.81 kB)
    - `dist/assets/index-gyP9e6Lh.js` (902.32 kB / gzip: 269.41 kB)
    - `dist/assets/manrope-DIRNzeTG.ttf` (164.70 kB)
    - `dist/assets/dm-sans-OkNhvBry.ttf` (240.16 kB)
- **Test Command:** `cd frontend; npm test`
  - Output: `vitest run`
  - Result: **Exit code 1**
  - Error: `No test files found, exiting with code 1`

---

## 3. Detailed Component & Feature Map of `App.tsx`

`App.tsx` defines 14 internal components and coordinates 9 pages/views plus 2 modals:

### 3.1 Global State (Root `App` Component, lines 186-236)
| State Variable | Type | Default | Description |
|---|---|---|---|
| `page` | `string` | `"Overview"` | Current active page view |
| `city` | `string` | `"Ahmedabad"` | Selected city (`Ahmedabad`, `Delhi`, `Hyderabad`) |
| `selectedId` | `string` | `""` | ID of selected analysis zone |
| `layer` | `string` | `"predicted_suhii"` | Active choropleth layer on map |
| `drawer` | `boolean` | `false` | Mobile drawer toggle |
| `dataOpen` | `boolean` | `false` | Data & Sources modal toggle |
| `tokenOpen` | `boolean` | `false` | Session API token modal toggle |
| `toast` | `string` | `""` | Global notification message |

### 3.2 TanStack Query & Mutation Map
| Query / Mutation | Method & Path | Invocation Location | Purpose |
|---|---|---|---|
| `overview` | `GET /api/overview?city={city}` | `App` root | Aggregated city statistics, model info, top priority zones |
| `map` | `GET /api/heat/map?city={city}` | `App` root | GeoJSON FeatureCollection with 1 km grid zone properties |
| `status` | `GET /api/data/status` | `App` root & `DataDialog` | Data provenance, DB engine, provider credentials, catalog |
| `exportReport` | `POST /api/reports/generate` | `App` topbar | Generates report and downloads Markdown |
| `train` | `POST /api/models/train` | `Prediction` page | Retrains ML models for selected city |
| `series` (dead code) | `GET /api/data/series` | `Prediction` page | Fetches Open-Meteo weather series (never displayed) |
| `explanation` | `POST /api/xai/explain` | `Explain` page | Fetches local TreeSHAP feature contributions for zone |
| `run` (Risk) | `POST /api/risk/analyze` | `Risk` page | Recomputes risk scores with custom exponents |
| `history` (Sim) | `GET /api/simulation/results?city={city}` | `Simulator` page | Fetches historical simulation scenarios |
| `run` (Sim) | `POST /api/simulation/run` | `Simulator` page | Runs physics/heuristic cooling simulation for zone |
| `run` (Optimizer) | `POST /api/optimization/run` | `Optimizer` page | Executes OR-Tools CP-SAT multi-zone intervention optimizer |
| `send` (Chat) | `POST /api/ai/chat` | `Assistant` page | Sends grounded user query to LLM (Groq / Gemini / Local) |
| `create` (Report) | `POST /api/reports/generate` | `Reports` page | Generates report and exposes MD/CSV/JSON download links |
| `ingest` | `POST /api/data/ingest` | `DataDialog` modal | Ingests live data from external providers or synthetic sample |

### 3.3 Page / View Breakdown
1. **Overview (`Overview`, lines 537-719):**
   - 4 KPI metric cards (`Metric`): Area Analyzed, Average Surface Heat, Heat Hotspots, Exposed Population.
   - Interactive `HeatMap` preview card with layer switcher.
   - "From the Evidence" model insights side card showing primary feature driver and quick navigation.
   - Priority zones ranking table (`ZoneTable`).
   - Global feature importance horizontal bar chart (`Importance`).
2. **Heat map (`HeatMap` + `ZoneDetails`, lines 437-450):**
   - Tall full-height Leaflet GeoJSON map with 8 choropleth layers:
     - `predicted_suhii`, `risk_score`, `ndvi`, `building_density`, `population_density`, `shap_ndvi`, `shap_ndbi`, `shap_building_density`.
   - Side panel `ZoneDetails` displaying zone thermal, vegetation, building, population, risk, and partition details.
3. **AI prediction (`Prediction`, lines 880-1019):**
   - Retrain models button triggering asynchronous training.
   - Model evaluation cards for Random Forest, XGBoost, and LightGBM comparing Test R², RMSE, MAE, and Validation RMSE.
   - Scatter plot of observed synthetic SUHII vs. predicted SUHII on the spatial test partition with 1:1 diagonal reference line.
   - Spatial partition graphic (training, validation, buffer, test ratio) and uncertainty interval summary.
   - *Flaw:* Fetches `series` from `/data/series` and extracts `meteorology`, but renders nothing with it.
4. **Explainable AI (`Explain`, lines 1020-1086):**
   - Zone picker.
   - Global feature importance chart.
   - Local zone SHAP waterfall / equation breakdown: Base value + local contributions = Predicted SUHII.
   - Spatial SHAP vegetation map (`shap_ndvi`).
5. **Heat risk (`Risk`, lines 1087-1202):**
   - Interactive exponent sliders ($w_H, w_E, w_V$) for $Risk = Hazard^{w_H} \times Exposure^{w_E} \times Vulnerability^{w_V}$.
   - Searchable priority zone table (search filter by zone name).
6. **Intervention simulator (`Simulator`, lines 1203-1425):**
   - Zone picker & constraint summary (available ground land, roof area, road area).
   - 8 intervention sliders (0-60% coverage, 5% step): trees, vegetation, parks, cool roofs, pavements, corridors, roof gardens, water.
   - Water availability input (m³/day).
   - Before/After comparison: Current SUHII vs. Scenario SUHII, hypothetical cooling, sensitivity range, water consumption, or constraint violation list.
   - Saved scenario history table.
7. **Optimization (`Optimizer`, lines 1426-1638):**
   - OR-Tools CP-SAT multi-zone optimizer configuration (water limit, vegetation limit, ground limit, min cooling).
   - Target zones: Top 5 priority zones.
   - Solution display: feasibility status, water consumption, mean cooling, population in selected zones, zone-by-zone intervention allocations, model explanation.
   - Low-water alternative plan card.
8. **AI assistant (`Assistant`, lines 1639-1785):**
   - Zone-grounded conversational interface.
   - Provider switcher (Auto, Groq, Gemini, Local).
   - Chat suggestions.
   - Grounded messages with citation fact IDs, recommended intervention action tags, and collapsible limitations/failures inspector.
9. **Reports (`Reports`, lines 1786-1942):**
   - Generates full reproducible analysis report.
   - Direct download links for Markdown, CSV, and JSON formats.
   - Provenance and connection status checker (DB, Groq, Gemini, Earth Engine).
10. **Data & Sources Dialog (`DataDialog`, lines 1943-2164):**
    - Ingestion interface for 8 data sources (Open-Meteo, OSM, Sentinel-2 STAC/indices, Earth Engine, WorldPop, OpenAQ, Sample).
    - Inputs for Lat, Lon, Dates, Rural Reference, GeoJSON Polygon.
    - Coverage catalog inspection.
11. **Workspace Settings Modal (lines 485-519):**
    - Browser session storage token manager for backend authentication.

---

## 4. Technical Debt, Typing, and Architectural Deficiencies

### 4.1 Type Safety & Pervasive `any`
Across `frontend/src/`, TypeScript strict mode is enabled in `tsconfig.json`, but bypassed everywhere by explicitly annotating parameters as `any`:
- In `api.ts`:
  ```typescript
  export async function api<T = any>(path: string, body?: unknown): Promise<T>
  ```
- In `App.tsx`:
  - `function Metric({ label, value, unit, detail, icon: Icon, tone = "green" }: any)`
  - `function ZonePicker({ data, selected, onSelect }: any)`
  - `function Overview({ overview: o, data, selected, onSelect, layer, onLayer, navigate }: any)`
  - `function ZoneTable({ zones, onSelect }: any)`
  - `function Importance({ data, local = false }: any)`
  - `function ZoneDetails({ selected: p, navigate }: any)`
  - `function Prediction({ city, data, overview, notify }: any)`
  - `function Explain({ city, data, selected, onSelect, overview }: any)`
  - `function Risk({ city, data, selected, onSelect }: any)`
  - `function Simulator({ city, data, selected, onSelect, notify }: any)`
  - `function Optimizer({ city, overview, notify }: any)`
  - `function Assistant({ city, data, selected, onSelect }: any)`
  - `function Reports({ city, overview, status, notify }: any)`
  - `function DataDialog({ city, close, notify }: any)`
- In `HeatMap.tsx`:
  - `export default function HeatMap({ data, layer, onLayer, selected, onSelect, tall = false }: { data: any; layer: string; onLayer: (v: string) => void; selected: string; onSelect: (p: any) => void; tall?: boolean })`
  - `style={(f: any) => ...}`

### 4.2 Missing Types
There are NO TypeScript definitions for:
- `ZoneProperties` (suhii, lst, ndvi, ndbi, ndwi, building_density, population, elderly_share, risk_score, risk_level, partition, shap, etc.)
- `ZoneFeatureCollection` & `ZoneFeature` (GeoJSON FeatureCollection)
- `CityOverview` (area_km2, average_suhii, hotspots, high_risk_zones, population_exposed, importance, model, priority_zones)
- `ModelEvaluation` & `ModelSplit`
- `SHAPExplanation` & `SHAPContribution`
- `SimulationResult` & `SimulationScenario`
- `OptimizationResult` & `ZoneSelection`
- `ChatResponse`, `AIFinding`, `ChatFact`
- `WeatherSeriesResponse` & `WeatherPoint`
- `DataStatus` & `CatalogItem`

### 4.3 Missing Features
1. **Multi-Zone Comparison (`ZoneComparison`):**
   - The user can only click one zone at a time. There is no multi-select mechanism, side-by-side metric comparison, or radar/difference chart comparing two or more zones (e.g. comparing High-Risk Sector 01 vs. Moderate-Risk Sector 05).
2. **Weather Time-Series Visualization:**
   - The backend `/api/data/series` returns hourly/daily weather data points (`air_temperature_c`, `relative_humidity_pct`, `hours_with_temperature`).
   - The frontend queries `/data/series` inside `Prediction` but discards it without rendering. Recharts `LineChart` and `Line` were imported but left unused.
3. **Interactive Boundary Sketch Integration:**
   - `BoundarySketch.tsx` is completely unused. In `DataDialog`, when a user selects `earth_engine` or `sample`, they are forced to type or paste raw JSON into a `<textarea>` instead of clicking on the map.
4. **Unutilized Backend Endpoints:**
   - `/api/heat/hotspots` (fast filtered hotspot list)
   - `/api/models` (model catalog)
   - `/api/optimization/results` (historical CP-SAT optimization runs)
   - `/api/data/records` (inspection of ingested weather, satellite, and OSM records)

### 4.4 Missing Test Suite
- `npm test` fails with code 1.
- No unit tests for `fmt`, `label`, `api`, or calculation utilities.
- No component tests for `Button`, `MetricCard`, `Badge`, `ZoneTable`, `Importance`, or `ZoneDetails`.

---

## 5. Comprehensive Modular Decomposition Plan

To transform this 2,164-line monolith into a modern, robust, type-safe architecture, the frontend will be restructured as follows:

```
frontend/src/
├── types/
│   ├── index.ts                   # Core domain types (City, LayerType, TabPage)
│   ├── geojson.ts                 # ZoneFeature, ZoneProperties, GeoJSON types
│   ├── overview.ts                # OverviewResponse, CityMetrics, ProvenanceMetadata
│   ├── ml.ts                      # ModelEvaluation, SplitGraphic, TreeSHAP
│   ├── simulation.ts              # Interventions, Constraints, Scenarios
│   ├── optimization.ts            # OR-Tools request/response, Selections
│   ├── weather.ts                 # Open-Meteo series, WeatherPoint, Trends
│   ├── chat.ts                    # Assistant messages, citations, limitations
│   └── data.ts                    # IngestPayload, DataStatus, CatalogItem
│
├── lib/
│   ├── utils.ts                   # cn helper, formatters (fmt, label, date, percentage)
│   └── constants.ts               # CITIES, PAGES, INTERVENTIONS, MAP_LAYERS, COLORS
│
├── services/
│   ├── api.ts                     # Strongly typed API client with error handling
│   ├── heatService.ts             # Overview, HeatMap, Hotspots
│   ├── mlService.ts               # Models, Train, Explain
│   ├── simulationService.ts       # Simulation runs, Scenario results
│   ├── optimizationService.ts     # CP-SAT runs & results
│   ├── dataService.ts             # Status, Series, Ingest, Records
│   └── chatService.ts             # LLM Chat stream/response
│
├── components/
│   ├── common/
│   │   ├── Button.tsx             # Radix Slot button primitive
│   │   ├── Card.tsx               # Card container with title, subtitle, actions
│   │   ├── Badge.tsx              # Tone-based badge (green, red, orange, blue, mint, neutral)
│   │   ├── MetricCard.tsx         # KPI Metric component with tone icons
│   │   ├── Notice.tsx             # System notice banner (info/error)
│   │   ├── Pending.tsx            # Loading spinner
│   │   ├── ErrorBoundary.tsx      # React error boundary for map/chart failsafes
│   │   └── Toast.tsx              # Toast notification renderer
│   │
│   ├── layout/
│   │   ├── Sidebar.tsx            # Navigation sidebar, brand, city card, data/settings links
│   │   ├── Topbar.tsx             # Breadcrumbs, demonstration pill, methodology link, avatar
│   │   ├── ContextBar.tsx         # Live analysis context bar with provenance link
│   │   └── Footer.tsx             # Application footer
│   │
│   ├── map/
│   │   ├── HeatMap.tsx            # Leaflet map with GeoJSON layer, strict typing
│   │   ├── MapLegend.tsx          # Dynamic gradient legend based on active layer
│   │   ├── MapLayerSelector.tsx   # Layer dropdown control
│   │   └── BoundarySketch.tsx     # Polygon boundary sketching tool
│   │
│   ├── charts/
│   │   ├── ImportanceBarChart.tsx # SHAP feature importance vertical bar chart
│   │   ├── ModelScatterChart.tsx  # Observed vs. Predicted SUHII scatter chart
│   │   ├── WeatherTimeSeriesChart.tsx # Recharts LineChart for temperature & humidity (NEW)
│   │   └── ZoneComparisonChart.tsx # Multi-zone bar/radar comparison chart (NEW)
│   │
│   ├── zone/
│   │   ├── ZonePicker.tsx         # Single zone selector dropdown
│   │   ├── ZoneTable.tsx          # Searchable, sortable zone priority table
│   │   ├── ZoneDetails.tsx        # Zone metric summary card
│   │   └── ZoneComparisonModal.tsx# Side-by-side multi-zone comparison view (NEW)
│   │
│   └── modals/
│       ├── DataDialog.tsx         # Ingestion dialog with integrated BoundarySketch
│       └── SettingsModal.tsx      # Backend session token modal
│
├── pages/
│   ├── OverviewPage.tsx           # Metrics grid, map preview, insights, top priorities
│   ├── HeatMapPage.tsx            # Full-height map with layer switcher & zone details
│   ├── PredictionPage.tsx         # Models, spatial scatter, split graphic, retrain action
│   ├── ExplainPage.tsx            # Global & local SHAP explanations, spatial variation map
│   ├── RiskPage.tsx               # Configurable risk formula (H×E×V), search & rankings
│   ├── SimulatorPage.tsx          # 8 intervention sliders, feasibility, scenario comparison
│   ├── OptimizerPage.tsx          # CP-SAT constraint optimizer, multi-zone intervention plan
│   ├── AssistantPage.tsx          # Grounded AI assistant chat with evidence citations
│   ├── ReportsPage.tsx            # Report generation, Markdown/CSV/JSON downloads, provenance
│   ├── WeatherPage.tsx            # Dedicated Weather Time-Series page or tab (Open-Meteo) (NEW)
│   └── ZoneComparePage.tsx        # Dedicated Zone Comparison page or modal (NEW)
│
├── hooks/
│   ├── useUrbanHeatData.ts        # Encapsulates overview, map, and status queries
│   └── useZoneComparison.ts       # Manages selected zones for comparison
│
├── tests/
│   ├── utils.test.ts              # Unit tests for formatters and helper functions
│   ├── Button.test.tsx            # Component test for Button
│   ├── Badge.test.tsx             # Component test for Badge
│   └── MetricCard.test.tsx        # Component test for MetricCard
│
└── App.tsx                        # Root orchestrator (<150 lines) with clean routing/tabs
```

---

## 6. Detailed Interface Design (TypeScript Models)

### `src/types/geojson.ts`
```typescript
export interface ZoneProperties {
  id: string;
  name: string;
  city: "Ahmedabad" | "Delhi" | "Hyderabad";
  spatial_block: number;
  row: number;
  column: number;
  area_km2: number;
  ndvi: number;
  ndwi: number;
  ndbi: number;
  ndbai: number;
  building_density: number;
  population_density: number;
  population: number;
  air_temperature: number;
  humidity: number;
  rainfall: number;
  solar_radiation: number;
  soil_moisture: number;
  land_cover: number;
  observed_suhii: number;
  predicted_suhii: number;
  predicted_lst: number;
  interval_low: number;
  interval_high: number;
  rural_reference: number;
  elderly_share: number;
  available_land_pct: number;
  roof_pct: number;
  road_pct: number;
  protected: boolean;
  source: string;
  acquired_at: string;
  risk_score: number;
  risk_level: "High" | "Moderate" | "Low";
  hotspot: boolean;
  partition: "train" | "val" | "test" | "buffer";
  shap: Record<string, number>;
}

export interface ZoneFeature {
  type: "Feature";
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
  properties: ZoneProperties;
}

export interface ZoneFeatureCollection {
  type: "FeatureCollection";
  features: ZoneFeature[];
  metadata: {
    city: string;
    center: [number, number];
    generated_at: string;
    source: string;
    synthetic: boolean;
    rural_reference_c?: number;
  };
}
```

### `src/types/weather.ts`
```typescript
export interface WeatherPoint {
  date: string;
  air_temperature_c: number;
  hours_with_temperature: number;
  relative_humidity_pct: number | null;
}

export interface WeatherSeries {
  id: string;
  source: string;
  latitude: number;
  longitude: number;
  synthetic: boolean;
  variable: string;
  points: WeatherPoint[];
}

export interface WeatherSeriesResponse {
  series: WeatherSeries[];
}
```

### `src/types/simulation.ts`
```typescript
export interface SimulationRequest {
  city: string;
  zone_id: string;
  name: string;
  coverage: Record<string, number>;
  water_limit: number;
  max_vegetation_pct?: number;
}

export interface SimulationResult {
  zone_id: string;
  coverage: Record<string, number>;
  feasible: boolean;
  violations: string[];
  before_suhii: number;
  after_suhii: number | null;
  estimated_cooling: number | null;
  sensitivity_range: [number, number] | null;
  water_m3_day: number;
  hypothetical: boolean;
  assumptions: string[];
}
```

---

## 7. New Feature Specifications

### 7.1 Weather Time-Series Integration
- **Component:** `src/components/charts/WeatherTimeSeriesChart.tsx`
- **Data Source:** `GET /api/data/series`
- **Visuals:** Dual Y-axis Recharts `ResponsiveContainer` + `LineChart` + `Line`:
  - Left Y-Axis: Daily Mean Air Temperature (°C) — Warm amber/orange line (`#d48244`).
  - Right Y-Axis: Relative Humidity (%) — Teal/cyan line (`#4f9999`).
  - Tooltip: Interactive date inspection with hours sampled.
  - Empty state: When no weather records exist, offers a one-click "Fetch Open-Meteo Weather" trigger calling `/api/data/ingest`.

### 7.2 Multi-Zone Comparison
- **Component:** `src/components/zone/ZoneComparisonModal.tsx` & `src/pages/ZoneComparePage.tsx`
- **User Experience:**
  - Planners can toggle checkboxes on `ZoneTable` rows to add zones to the comparison tray (up to 4 zones).
  - Side-by-side metric comparison cards:
    - Thermal: SUHII, LST, Rural Reference
    - Land Cover: NDVI, NDBI, Building Density
    - Demographics: Population Density, Elderly Share, Risk Score
    - Interventions: Available Ground %, Roof %, Road %
  - Multi-bar chart comparing SUHII and Risk Scores across selected zones.
  - Quick action to launch simulation on any compared zone.

### 7.3 BoundarySketch Re-integration
- **Component:** `src/components/map/BoundarySketch.tsx`
- **Integration:** Embed directly into `DataDialog.tsx` under a "Draw on Map" tab alongside "Manual GeoJSON".
- **User Experience:** Planners click vertices directly on the Leaflet map to outline their urban study boundary, click "Close Polygon", and the valid GeoJSON Polygon is automatically populated and validated.

---

## 8. Verification & Test Plan

1. **Vitest Unit & Component Tests:**
   - Add test runner configuration in `vite.config.ts` (`test: { globals: true, environment: 'happy-dom' }`).
   - Add tests:
     - `src/lib/utils.test.ts`: test `cn`, `fmt`, `label`
     - `src/components/common/Button.test.tsx`: test button render, variants, onClick
     - `src/components/common/Badge.test.tsx`: test tones and children
   - Run `npm test` -> must pass with exit code 0.
2. **Build Verification:**
   - Run `npm run build` -> must pass with exit code 0 and modular code splitting.
3. **End-to-End Visual Verification:**
   - All 9 existing pages function identically or better.
   - New Weather Time-Series chart renders seamlessly.
   - Multi-Zone comparison correctly contrasts zones.
   - Polygon sketching works without errors.
