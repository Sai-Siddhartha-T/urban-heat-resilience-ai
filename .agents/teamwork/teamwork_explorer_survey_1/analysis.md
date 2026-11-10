# Technical Analysis Report — Survey 1: Frontend Architecture, UI/UX Redesign, Navigation & Geospatial Map

**Date**: 2026-11-10  
**Agent**: Teamwork Explorer (Survey 1)  
**Target Codebase**: `d:\Urban-Heat-Resilience-AI\frontend\`  
**Scope**: Requirements R1 & R4 (World-Class Dark-First Climate Intelligence UI, Palantir-Style Geospatial Mapping, 10 Views, Application Shell, API Contracts)  

---

## 1. Executive Summary

A comprehensive investigation of the Heatwise frontend architecture was conducted to evaluate readiness against requirements **R1** (World-Class Frontend Redesign & Climate Intelligence UI) and **R4** (Geospatial Platform and Interactive Mapping System).

### Key Findings
1. **Build & Test Health**: The frontend builds successfully with zero TypeScript compilation errors (`tsc -b && vite build` transforms 2,112 modules in 26.4s). The test suite (`vitest run`) executes 11 test files with **91 passing tests**, covering hash routing, API client error handling, multi-zone selection, sidecar viewer linkages, and evidence workspace states.
2. **Design System Gap**: The current frontend is styled in a **light-theme olive/pastel palette** (`#f6f8f5` background, `#263d34` dark green text, `#eaf2e9` light green cards in `frontend/src/styles.css`). This directly contradicts requirement R1, which mandates a **premium, dark-first climate-intelligence platform** combining Palantir-style geospatial intelligence with Linear-level interface precision.
3. **Application Shell & Navigation Gaps**: 
   - The current `Sidebar` (`Sidebar.tsx:20-58`) is fixed at 238px width, with no collapsible state, no icon-only mode, and no mobile responsive drawer.
   - The current `Topbar` (`Topbar.tsx:17-60`) only hosts city buttons and status badges. It lacks the required **top command bar** (`⌘K` / `Ctrl+K` command palette, omni-search for cities and zones, quick action execution).
   - Currently, the navigation model exposes 10 tabs, but they do not match the canonical 10 views required by R1: specifically, there is **no dedicated Environmental Analysis view** (weather, air quality, groundwater), while "Heat Analysis" is fragmented across prediction and comparison tabs.
4. **Geospatial Map (`HeatMap.tsx`) Deficiencies**:
   - Uses basic OpenStreetMap tiles on a light beige background (`#edece2`) rather than dark CartoDB Matter / dark tiles.
   - Only visualizes polygon analytical zones with a single `<select>` layer dropdown.
   - **Completely lacks multi-layer support**: cannot overlay point stations (OpenAQ air quality, Open-Meteo weather, CGWB groundwater), continuous satellite LST, land cover classification, or proposed interventions simultaneously.
   - Missing opacity sliders, physical-unit legends for multiple data types, time-period/date filters, and search-to-zone zooming.
5. **Contract Compatibility**: Existing tests rely on `useHashRouter`, `PAGE_MAP`, and specific sidecar URL links (`sidecar://biomolecular_structure_viewer` for raster layers in `ZoneDetails.tsx`). The architectural upgrade for Agent 7 must retain these contracts as backward-compatible foundations while introducing the upgraded dark system and expanded views.

---

## 2. Codebase Architecture & Technical Audit

### 2.1 Technology Stack

| Layer | Technology | Version | Location / Config |
|---|---|---|---|
| Runtime & Bundler | Vite | `^7.1.0` | `frontend/vite.config.ts` |
| UI Framework | React | `^19.1.0` | `frontend/package.json` |
| Language | TypeScript | `~5.9.2` | `frontend/tsconfig.json` |
| Styling Engine | Tailwind CSS v4 | `^4.1.0` + `@tailwindcss/vite` | `frontend/src/styles.css` |
| Server State | TanStack React Query | `^5.90.0` | `frontend/src/App.tsx:17-19` |
| Icons | Lucide React | `^0.468.0` | `frontend/src/lib/constants.ts` |
| Charts | Recharts | `^3.0.0` | `frontend/src/components/charts/` |
| Mapping Engine | Leaflet + React-Leaflet | `^1.9.4` / `^5.0.0` | `frontend/src/components/HeatMap.tsx` |
| Test Runner | Vitest | `^3.2.0` | `frontend/src/tests/` |

### 2.2 Directory Structure & Module Distribution

```
frontend/src/
├── assets/                  # Custom webfonts: DM Sans, Manrope
├── components/
│   ├── charts/              # Recharts implementations (ImportanceBarChart, WeatherTimeSeriesChart, ZoneComparisonChart)
│   ├── common/              # UI primitives (Badge, Button, Card, MetricCard, Notice, Pending, SyntheticWarningBadge)
│   ├── evidence/            # EvidenceLayerPreview (Raw SVG preview for non-analyzed assets)
│   ├── layout/              # Sidebar.tsx, Topbar.tsx, PageHeader.tsx, ContextBar.tsx
│   ├── modals/              # DataDialog.tsx (Data sources ingestion & demo mode trigger)
│   ├── zone/                # ZoneDetails.tsx, ZonePicker.tsx, ZoneTable.tsx
│   ├── BoundarySketch.tsx   # Polygon boundary drawer
│   ├── button.tsx           # Radix Slot button primitive
│   └── HeatMap.tsx          # Leaflet map container & GeoJSON renderer
├── hooks/
│   └── useHashRouter.ts     # Window hash router with query parameter synchronization
├── lib/
│   ├── constants.ts         # PAGES, PAGE_MAP, CITIES, MAP_LAYERS, interventionNames
│   ├── raster.ts            # RASTER_LAYERS catalog and isRasterLayer() classifier
│   └── utils.ts             # fmt, label, risk calculations, selection state helpers
├── pages/
│   ├── AssistantPage.tsx    # Grounded AI Chat with Groq/Gemini/Local
│   ├── EvidenceWorkspacePage.tsx # Normal-mode evidence inspector
│   ├── ExplainPage.tsx      # TreeSHAP global and local waterfall
│   ├── MapPage.tsx          # Map with ZoneDetails inspector
│   ├── NormalModeContent.tsx# Switcher between evidence workspace and analysis mode
│   ├── OptimizerPage.tsx    # CP-SAT physical constraint optimizer
│   ├── OverviewPage.tsx     # Overview dashboard
│   ├── PredictionsPage.tsx  # ML model evaluations, R² scatter, weather time-series
│   ├── ReportsPage.tsx      # Report generation and download links
│   ├── RiskPage.tsx         # Hazard × Exposure × Vulnerability weight sliders
│   ├── SimulatorPage.tsx    # Intervention simulator
│   └── ZoneComparePage.tsx  # Radar and comparative bar analysis for up to 4 zones
├── services/                # Typed API client & resource services (11 service files)
├── tests/                   # 11 Vitest test suites
├── types/                   # TypeScript interfaces and domain models (12 definition files)
├── App.tsx                  # Root state orchestration & route dispatching
├── main.tsx                 # React DOM mount point
└── styles.css               # 2,455 lines of legacy light-theme styles
```

### 2.3 Verification of Build and Test Systems

The test command and build command were directly executed in the workspace:

#### Test Execution:
```bash
npm --prefix frontend test
# Vitest output:
# Test Files: 11 passed (11)
# Tests:      91 passed (91)
# Duration:   10.69s
```
All suites pass:
1. `src/tests/weather.test.ts` (3 tests)
2. `src/tests/zoneCompare.test.ts` (6 tests)
3. `src/tests/metrics.test.ts` (11 tests)
4. `src/tests/evidenceApi.test.ts` (2 tests)
5. `src/tests/integration_challenge.test.ts` (18 tests)
6. `src/tests/syntheticWarningBadge.test.tsx` (10 tests)
7. `src/tests/button.test.tsx` (5 tests)
8. `src/tests/normalModeContent.test.tsx` (3 tests)
9. `src/tests/mapPageSidecar.test.tsx` (5 tests)
10. `src/tests/api.test.ts` (24 tests)
11. `src/tests/evidenceWorkspace.test.tsx` (4 tests)

#### Build Execution:
```bash
npm --prefix frontend run build
# vite v7.3.7 building client environment for production...
# transforming...
# ✓ 2112 modules transformed.
# rendering chunks...
# dist/index.html                     0.53 kB │ gzip:   0.35 kB
# dist/assets/manrope-DIRNzeTG.ttf  164.70 kB
# dist/assets/dm-sans-OkNhvBry.ttf  240.16 kB
# dist/assets/index-Cf8God1b.css     64.99 kB │ gzip:  18.18 kB
# dist/assets/index-Dzfsb2An.js     975.79 kB │ gzip: 289.43 kB
# ✓ built in 26.38s
```
**Conclusion on build/test**: The existing codebase is stable, compilable, and passes all tests. It provides a solid baseline for structural refactoring.

---

## 3. Gap Analysis Against R1 & R4 Requirements

### 3.1 Design System & Aesthetic (R1)

| Aspect | Current Implementation | Requirement (R1) | Required Transformation |
|---|---|---|---|
| **Theme / Color Palette** | Light-only pastel theme (`#f6f8f5` canvas, `#263d34` text, `#eaf2e9` light green badges, `#315f4b` buttons in `styles.css:15-22`) | Premium, modern, **dark-first climate-intelligence** design system | Adopt dark slate/obsidian palette (`#090d12`, `#0e141d`, `#161f2c`, `#1e293b`), hair-line borders (`rgba(255,255,255,0.08)`), high-contrast thermal gradients. |
| **Aesthetic Standard** | Organic research paper/municipal portal aesthetic | **Palantir-style geospatial intelligence** + **Linear-level interface precision** | Monospace metrics (`font-mono`), micro-badges, tabular figures, subtle glow accents (`box-shadow: 0 0 15px rgba(16, 185, 129, 0.15)`), crisp typography. |
| **Application Shell** | Static sidebar (fixed 238px width, `styles.css:105-116`), static top header | **Collapsible navigation** + **Top Command Bar** | Implement collapsible sidebar (expanded 240px, collapsed 64px icon-only, mobile overlay drawer); add global `⌘K` / `Ctrl+K` command bar. |
| **Motion & Micro-interactions** | Minimal CSS hover color transitions | Purposeful animations, smooth micro-interactions | Micro-transitions on tab switches, pulsating radar rings on active sensor stations, smooth drawer slides, skeleton loaders. |
| **Responsiveness** | Partial media queries (`max-width: 1690px`), fixed widths cause tablet/mobile cramping | Fully responsive across desktop, tablet, and mobile | Flex/grid layouts with `minmax(0, 1fr)`, collapsible sidebars with touch backdrops, scrollable telemetry ribbons. |

### 3.2 Navigation Architecture & 10 Canonical Views (R1)

Requirement R1 states:
> *"redesign all pages (Overview Command Center, Live Environmental Map, Heat Analysis, Environmental Analysis, Heat Risk & Vulnerability, Explainable AI, Mitigation Planning, Intervention Optimization, AI Climate Assistant, Reports)"*

Comparison matrix of views:

| # | Required Canonical View (R1) | Current View / Page Slug | Current File | Gaps & Required Upgrades |
|---|---|---|---|---|
| 1 | **Overview Command Center** | `Overview` (`overview`) | `OverviewPage.tsx` | Upgrade into high-density mission control: city-wide telemetry sparklines, real-time alert feed, active hotspot summary, direct jump to priority zones, live weather status badge. |
| 2 | **Live Environmental Map** | `Heat map` (`map`) | `MapPage.tsx`, `HeatMap.tsx` | Transform into multi-layer geospatial engine: dark tile base, layer toggles for 12+ physical layers, station pin overlays, opacity sliders, physical unit legends, zone inspector flyout. |
| 3 | **Heat Analysis** | `Zone comparison` (`compare`) + `AI prediction` (`prediction`) | `ZoneComparePage.tsx`, `PredictionsPage.tsx` | Unify predictive heat analytics, observed LST vs predicted LST vs SUHII comparison, thermal distribution curves, spatial error analysis, and cross-sector thermal disparity. |
| 4 | **Environmental Analysis** | *Missing* (weather series was buried in PredictionsPage) | *New Component Needed* | Create dedicated Environmental Analysis view synthesizing: atmospheric conditions (Open-Meteo), air quality monitor network (OpenAQ/CPCB), groundwater trends (CGWB), and spectral indices (NDVI/NDBI/NDWI). |
| 5 | **Heat Risk & Vulnerability** | `Heat risk` (`risk`) | `RiskPage.tsx` | Refine Hazard × Exposure × Vulnerability decomposition with real demographic data indicators (elderly share, poverty index, healthcare access), interactive risk matrix, and vulnerability profiles. |
| 6 | **Explainable AI** | `Explainable AI` (`explain`) | `ExplainPage.tsx` | TreeSHAP global feature importance, zone-specific waterfall contribution breakdown, spatial SHAP map overlay, and clear causal vs associative scientific disclaimers. |
| 7 | **Mitigation Planning** | `Intervention simulator` (`simulator`) | `SimulatorPage.tsx` | Literature-grounded cooling mechanisms (tree canopy, green roofs, cool pavements, urban water bodies), spatial land availability constraints, uncertainty intervals (±30-40%), before/after comparison. |
| 8 | **Intervention Optimization** | `Optimization` (`optimizer`) | `OptimizerPage.tsx` | Constraint-based optimization (OR-Tools CP-SAT) without financial budgets; multi-zone allocation maps, Pareto cooling vs water feasibility trade-offs, spatial priority plans. |
| 9 | **AI Climate Assistant** | `AI assistant` (`assistant`) | `AssistantPage.tsx` | Grounded chat interface with Groq / Gemini provider fallback, citations of actual backend zone metrics and sensor readings, quick prompt chips, and graceful offline degradation. |
| 10 | **Reports** | `Reports` (`reports`) | `ReportsPage.tsx` | Executive summary generator, custom analytical report builder, export to Markdown, PDF, CSV, and GeoJSON; verification provenance appendix. |

### 3.3 Geospatial Platform & Interactive Mapping System (R4)

Current `HeatMap.tsx` has significant architectural limitations:

1. **Tile Layer Basemap**:
   - Current: Hardcoded `url="/api/tiles/{z}/{x}/{y}.png"` (`HeatMap.tsx:77`), which proxies OpenStreetMap standard tiles (light background).
   - Requirement: Dark-first basemap. Should use CartoDB Dark Matter (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) or dark-styled OSM tiles with smooth dark container backgrounds (`#0a0f16`).
2. **Layer Support**:
   - Current: Supports only 1 GeoJSON layer at a time via a dropdown (`HeatMap.tsx:110-121`), styling polygon fill colors using a single helper `color()` function.
   - Missing Required Layers:
     - **Observed Land Surface Temperature (LST)** in °C (satellite remote sensing).
     - **Predicted Surface Temperature** vs **Predicted SUHII** in °C.
     - **Land Cover** categorical classification (ESA WorldCover: built-up, tree cover, shrubland, cropland, water, bare).
     - **Spectral Indices**: NDVI (vegetation), NDWI (water), NDBI (built-up).
     - **Air Quality Stations**: Point markers for OpenAQ/CPCB stations with live PM2.5, PM10, AQI status badges.
     - **Weather Stations**: Point markers for Open-Meteo observation points (air temp, RH, wind speed).
     - **Groundwater Stations**: Point markers for CGWB monitoring wells (water table depth in meters below ground level).
     - **Population Exposure**: Gridded population counts from WorldPop/GHSL.
     - **Proposed Interventions**: Spatial layer displaying planned cool roofs, urban forests, and permeable surfaces.
3. **Layer Controls & Opacity**:
   - Current: Single select dropdown.
   - Requirement: Multi-layer toggle stack with individual layer checkboxes, reorderable visual hierarchy, and per-layer opacity sliders (0–100%).
4. **Legends & Physical Units**:
   - Current: Single static color bar with generic "Lower / Higher" labels (`HeatMap.tsx:131-157`).
   - Requirement: Dynamic legends showing actual physical units:
     - LST & SUHII: `°C` with real thermal range (e.g., 28°C to 48°C)
     - NDVI / NDWI / NDBI: normalized index `[-1.0, +1.0]`
     - Building Density: `%` `[0% to 100%]`
     - Population Density: `inhabitants / km²`
     - Air Quality PM2.5: `µg/m³` (with standard CPCB/WHO health thresholds)
     - Groundwater Depth: `meters below ground level (mbgl)`
     - SHAP values: local additive contribution `°C`
5. **Interactive Zone Inspection & Tooltips**:
   - Current: Simple tooltip `f.properties.name` + `SUHII: ...` (`HeatMap.tsx:99-103`).
   - Requirement: Rich interactive zone hover tooltips, click-to-inspect flyout side panel displaying multi-parameter telemetry, and sidecar link for raster layers (`data-testid="zone-sidecar-link"`).

---

## 4. Design System Specification for Agent 7

To deliver on R1 and R4, Agent 7 should implement a cohesive dark design system adhering to the following tokens:

### 4.1 Color Tokens (Tailwind & CSS Variables)

```css
:root {
  /* Canvas & Surfaces */
  --bg-app: #080c11;            /* Deep obsidian app canvas */
  --bg-surface: #0e141d;        /* Base panel / sidebar / card background */
  --bg-surface-elevated: #151d2a;/* Hover, elevated cards, dropdowns */
  --bg-surface-overlay: #1b2637; /* Dialogs, flyouts, command bar */
  
  /* Borders & Dividers */
  --border-subtle: rgba(255, 255, 255, 0.07);
  --border-default: rgba(255, 255, 255, 0.12);
  --border-strong: rgba(255, 255, 255, 0.20);
  --border-accent: rgba(16, 185, 129, 0.4);

  /* Typography */
  --text-primary: #f1f5f9;       /* Slate 100 */
  --text-secondary: #94a3b8;     /* Slate 400 */
  --text-tertiary: #64748b;      /* Slate 500 */
  --text-accent: #34d399;        /* Mint 400 */

  /* Climate / Domain Accents */
  --color-thermal-heat: #ef4444; /* High thermal risk / SUHII hotspot */
  --color-thermal-warm: #f97316; /* Moderate heat / built-up */
  --color-thermal-mid: #eab308;  /* Intermediate transition */
  --color-vegetation: #10b981;   /* NDVI / green infrastructure */
  --color-water: #06b6d4;        /* NDWI / water bodies / moisture */
  --color-air-quality: #a855f7;  /* PM2.5 / atmospheric monitoring */
  --color-groundwater: #3b82f6;  /* Aquifer / groundwater well depth */
}
```

### 4.2 Application Shell Architecture

```
+---------------------------------------------------------------------------------------------------+
| Topbar / Command Bar (Height: 56px)                                                               |
| [Logo: Heatwise] [City Picker: Ahmedabad v] [Ctrl+K Omnisearch] [Data Status] [Demo Pill] [Avatar]|
+-----------------------+---------------------------------------------------------------------------+
| Collapsible Sidebar   | Main Content Area (Dynamic Page View)                                     |
| (240px <-> 64px)      |                                                                           |
|                       |  [Page Header: Eyebrow | Title | Live Badges | Action Buttons]            |
| - Overview Center     |  -----------------------------------------------------------------------  |
| - Live Map (GIS)      |                                                                           |
| - Heat Analysis       |  [Active View: 1 of 10 Canonical Views]                                   |
| - Environmental Analy |                                                                           |
| - Heat Risk & Vuln    |                                                                           |
| - Explainable AI      |                                                                           |
| - Mitigation Planning |                                                                           |
| - Optimization Engine |                                                                           |
| - AI Assistant        |                                                                           |
| - Reports & Export    |                                                                           |
|                       |                                                                           |
| [Telemetry Footer]    |                                                                           |
+-----------------------+---------------------------------------------------------------------------+
```

### 4.3 Command Bar (`Ctrl+K` / `⌘K`) Interactions
- Omnisearch palette listening to `keydown` (`e.key === "k" && (e.metaKey || e.ctrlKey)`).
- Quick navigation to any of the 10 views.
- Quick city switching: "Switch to Delhi", "Switch to Hyderabad", "Switch to Ahmedabad".
- Quick zone search: Type "Sector 01" or "DEL_04" to zoom and inspect directly.
- Quick action triggers: "Retrain Models", "Run CP-SAT Optimization", "Download Heat Report", "Ask Climate AI".

---

## 5. Frontend-Backend API Contracts Specification

The frontend expects strict, typed contracts from the backend (`backend/app/routes/`). Below is the verified API contract reference for Agent 6 and Agent 7.

### 5.1 System, Health & Metadata
- **`GET /api/health`**
  - Query: `city?: CityName`, `mode?: "normal" | "demo"`
  - Response:
    ```typescript
    interface HealthResponse {
      status: "ok";
      database: string; // "PostgreSQL/PostGIS" | "SQLite local fallback"
      synthetic_predictions: boolean;
      analysis_ready: boolean;
      mode: "normal" | "demo";
      schema_revision: string | null;
      city?: string;
    }
    ```
- **`GET /api/cities`**
  - Response: `Array<{ name: City; center: [number, number] }>`

### 5.2 Overview & Spatial Heat
- **`GET /api/overview`**
  - Query: `city: CityName`, `mode?: "normal" | "demo"`
  - Response:
    ```typescript
    interface OverviewResponse {
      city: City;
      area_km2: number;
      zone_count: number;
      average_suhii: number;
      hotspots: number;
      high_risk_zones: number;
      population_exposed: number;
      priority_zones: ZoneProperties[];
      importance: FeatureImportance[];
      model: ModelSummaryMetadata;
    }
    ```
- **`GET /api/heat/map`**
  - Query: `city: CityName`, `mode?: "normal" | "demo"`
  - Response: `ZoneFeatureCollection` (GeoJSON FeatureCollection where each Feature contains `ZoneProperties` with polygon coordinates).
- **`GET /api/heat/hotspots`**
  - Query: `city: CityName`, `mode?: "normal" | "demo"`
  - Response: `ZoneProperties[]` (filtered where `hotspot === true`).
- **`POST /api/heat/predict`** and **`GET /api/heat/predict`**
  - Request: `{ city: City; zone_id?: string; mode?: "normal" | "demo" }`
  - Response: `PredictionResponse | PredictionBatchResponse`.

### 5.3 Environmental & Station Monitoring (R3 & R4 Contracts)
- **`GET /api/data/series`**
  - Query: `city?: string`
  - Response:
    ```typescript
    interface WeatherDataResponse {
      series: WeatherSeries[]; // hourly/daily observations with air_temperature_c, relative_humidity_pct, rainfall_mm, solar_radiation_mj_m2_day
      note?: string;
    }
    ```
- **`GET /api/environmental/stations`** *(Recommended endpoint for Agent 6 & 7)*
  - Query: `city: CityName`, `category?: "weather" | "air_quality" | "groundwater"`
  - Response:
    ```typescript
    interface EnvironmentalStationCollection {
      type: "FeatureCollection";
      features: Array<{
        type: "Feature";
        geometry: { type: "Point"; coordinates: [number, number] }; // [lon, lat]
        properties: {
          id: string;
          name: string;
          network: "OpenAQ" | "CPCB" | "Open-Meteo" | "CGWB" | "India-WRIS";
          category: "air_quality" | "weather" | "groundwater";
          last_updated: string;
          distance_to_center_km?: number;
          metrics: {
            pm25?: number; // µg/m³
            pm10?: number; // µg/m³
            no2?: number;  // µg/m³
            aqi?: number;
            air_temperature?: number; // °C
            humidity?: number;        // %
            wind_speed?: number;      // m/s
            water_depth_mbgl?: number;// meters below ground level
            water_level_trend?: "rising" | "stable" | "declining";
          };
        };
      }>;
    }
    ```

### 5.4 Machine Learning & Explainable AI (R5)
- **`GET /api/models`**
  - Query: `city: CityName`
  - Response:
    ```typescript
    interface ModelSummary {
      winner: "RandomForest" | "XGBoost" | "LightGBM";
      split: { method: string; training: number; validation: number; buffer: number; test: number };
      evaluations: Array<{
        model: string;
        test: { r2: number; rmse: number; mae: number; bias?: number };
        validation: { r2: number; rmse: number; mae: number };
      }>;
    }
    ```
- **`POST /api/models/train`**
  - Body: `{ city: City }`
  - Response: `ModelSummary`
- **`POST /api/xai/explain`**
  - Body: `{ city: City; zone_id: string }`
  - Response:
    ```typescript
    interface TreeSHAPExplanation {
      zone_id: string;
      prediction: number; // predicted SUHII (°C)
      base_value: number; // expected model baseline E[f(x)] (°C)
      contributions: Record<string, number>; // feature name -> additive SHAP contribution in °C
    }
    ```
- **`GET /api/xai/importance`**
  - Query: `city: CityName`
  - Response: `Array<{ feature: MLFeatureName; importance: number; std?: number }>`

### 5.5 Risk Assessment (R6)
- **`POST /api/risk/analyze`**
  - Body: `{ city: City; hazard_weight: number; exposure_weight: number; vulnerability_weight: number }`
  - Response:
    ```typescript
    interface RiskAnalysisResponse {
      city: City;
      formula: string;
      zones: Array<{
        zone_id: string;
        risk_score: number; // [0, 100]
        hazard: number;     // [0, 1]
        exposure: number;   // [0, 1]
        vulnerability: number; // [0, 1]
        risk_level: "High" | "Moderate" | "Low";
        missing_indicators: string[];
      }>;
    }
    ```

### 5.6 Simulation & Physical Optimization (R6)
- **`GET /api/interventions`**
  - Response: `{ interventions: Record<InterventionType, InterventionSpec>; assumptions: string[] }`
- **`POST /api/simulation/run`**
  - Body:
    ```typescript
    interface SimulationRequest {
      city: City;
      zone_id: string;
      name: string;
      coverage: Record<string, number>; // intervention_type -> coverage %
      water_limit: number;              // m³/day
      max_vegetation_pct: number;
    }
    ```
  - Response:
    ```typescript
    interface SimulationResponse {
      scenario_id: string;
      zone_id: string;
      feasible: boolean;
      cooling_effect_c: number;          // Expected cooling in °C
      uncertainty_low_c: number;
      uncertainty_high_c: number;
      water_required_m3_day: number;
      violations: string[];
      assumptions: string[];
    }
    ```
- **`POST /api/optimization/run`**
  - Body:
    ```typescript
    interface OptimizationRequest {
      city: City;
      zone_ids?: string[];
      water_limit: number;
      max_vegetation_pct: number;
      land_limit_pct: number;
      min_cooling: number;
    }
    ```
  - Response:
    ```typescript
    interface OptimizationResponse {
      optimization_id: string;
      city: City;
      status: "OPTIMAL" | "FEASIBLE" | "INFEASIBLE";
      allocations: ZoneAllocation[];
      total_cooling_c: number;
      total_water_used: number;
      zones_treated: number;
    }
    ```

### 5.7 Grounded AI Assistant & Reports (R7)
- **`POST /api/ai/chat`**
  - Body: `{ city: City; zone_id?: string; message: string; provider: "auto" | "groq" | "gemini" | "local" }`
  - Response:
    ```typescript
    interface ChatResponse {
      answer: string;
      provider: string;
      model: string;
      sources: Array<{ name: string; type: string; timestamp?: string }>;
      findings?: string[];
      error?: string;
    }
    ```
- **`POST /api/reports/generate`**
  - Body: `{ city: City }`
  - Response: `{ id: string; download_url: string; csv_url: string; markdown_url: string }`

---

## 6. Implementation Action Plan for Agent 7

To execute R1 and R4 cleanly without breaking regressions, Agent 7 should follow this sequenced roadmap:

### Phase 1: Design System & Styling Foundation
1. **Dark Theme Variables**: Upgrade `frontend/src/styles.css` with a comprehensive dark-first design token set (obsidian canvas, slate surfaces, hairline borders, emerald/amber/flame accents).
2. **Tailwind v4 Integration**: Verify `@theme` blocks or utility definitions in Tailwind v4 configuration to allow rapid UI composition.
3. **Common UI Primitives**: Redesign `Card`, `Badge`, `Button`, `MetricCard`, and `Notice` to render with modern dark-surface styles, glassmorphic headers, and crisp monospace numbers.

### Phase 2: Application Shell & Navigation
1. **Collapsible Sidebar**: Refactor `Sidebar.tsx` to support expanded (240px) and collapsed (64px icon-only with tooltips) states, plus a mobile slide-over drawer with toggle button.
2. **Top Command Bar**: Implement a comprehensive `Topbar.tsx` featuring:
   - Target city selector tabs/dropdown
   - `Ctrl+K` / `⌘K` Command Palette component (`CommandDialog`)
   - Data provenance & DB status pill
   - Real evidence vs demonstration mode indicator
3. **Route Mapping & Aliases**: In `constants.ts` and `routes.ts`, register the 10 canonical views while maintaining existing slugs (`prediction`, `compare`, `simulator`, `optimizer`) as backward-compatible aliases so all 91 existing tests continue passing without modification.

### Phase 3: Geospatial Map Overhaul (R4)
1. **Dark Tile Basemap**: Configure Leaflet with CartoDB Dark Matter tiles (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) with graceful fallback to dark-inverted OSM.
2. **Multi-Layer System**:
   - Refactor `HeatMap.tsx` to accept a `layers` configuration supporting multiple active layers simultaneously.
   - Implement point marker layers for Weather stations, Air Quality monitoring stations, and Groundwater monitoring wells with custom SVG icon pins and popup cards.
   - Implement continuous/stepped choropleth shaders for LST, SUHII, NDVI, Built-up Density, and Land Cover.
3. **Map HUD Controls**:
   - Floating Layer Control panel with toggle switches.
   - Per-layer Opacity Sliders (0% to 100%).
   - Dynamic Physical-Unit Legends showing accurate min/max stops and units (`°C`, `µg/m³`, `mbgl`, `[-1, 1]`, `%`).
   - Zone Inspection Flyout displaying detailed metrics and preserving the required sidecar viewer link (`data-testid="zone-sidecar-link"`).

### Phase 4: Page Redesign across 10 Views
1. **Overview Command Center**: Mission control layout with key telemetry, live station metrics, prioritized hotspots, and action shortcuts.
2. **Live Environmental Map**: Full-viewport geospatial workspace with layer controls and inspection drawer.
3. **Heat Analysis**: Consolidate model performance scatter plots, spatial validation partitions, and multi-zone heat disparity comparison.
4. **Environmental Analysis**: Build dedicated view for Open-Meteo time-series, OpenAQ air pollution levels, and CGWB groundwater trends.
5. **Heat Risk & Vulnerability**: H × E × V interactive formulation, risk distribution chart, and priority rankings.
6. **Explainable AI**: TreeSHAP global feature importance, zone-specific waterfall breakdowns, and spatial SHAP maps.
7. **Mitigation Planning**: Intervention simulator with cooling ranges, land constraints, and before/after comparisons.
8. **Intervention Optimization**: CP-SAT solver results, resource allocation heat map, and feasibility metrics.
9. **AI Climate Assistant**: Conversational grounded chat interface with role prompts, citations, and model selector.
10. **Reports**: Report builder with Markdown preview, metadata provenance audit, and download actions.

### Phase 5: Verification & Integration Tests
1. Run `npm test` after each phase to guarantee zero regressions across the 91 existing tests.
2. Add new test suites for the Command Palette, collapsible sidebar state, and multi-layer map toggles.
3. Run `npm run build` to verify clean production compilation.

---

*Report prepared by Teamwork Explorer (Survey 1).*
