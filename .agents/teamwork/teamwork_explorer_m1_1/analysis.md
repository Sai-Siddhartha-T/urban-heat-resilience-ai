# Frontend Page Decomposition & Routing Architecture Specification

**Author:** Explorer M1-1 — Frontend Page Decomposition & Routing Specialist  
**Target:** `frontend/src/App.tsx` (2,164 lines)  
**Date:** 2026-11-08  
**Scope:** Milestone 1 (Frontend Modularization)  

---

## 1. Executive Summary & Problem Statement

The frontend of Heatwise is currently packaged into a single monolithic file: `frontend/src/App.tsx` (2,164 lines, 80 KB). This monolith contains:
- 14 co-located component definitions (primitives, tables, charts, cards, modals).
- 9 views/tabs switched via raw string state (`page === "Overview"`, etc.).
- 3 TanStack queries and 7 mutations.
- Unused Lucide icons (`BarChart3`, `CloudSun`, `MessageSquare`, `Zap`), dead Recharts imports (`LineChart`, `Line`), and an orphaned query to `/data/series` (lines 882-886).
- Unrendered Leaflet sketcher component (`BoundarySketch.tsx`, 117 lines).
- Missing features: Multi-Zone Comparison view (Feature 4) and Weather Time-Series chart (Feature 5).
- Zero test coverage (`vitest run` fails with exit code 1).
- Unchunked single bundle build (902.32 kB JS).

This specification delineates the exact page boundaries for splitting `App.tsx` into **10 modular pages**, extracts reusable layout and UI components, establishes a **zero-dependency, deep-linkable hash router with browser history synchronization**, and slims down `App.tsx` into a clean orchestrator of **under 150 lines**.

---

## 2. Monolith Inventory & Component Map

### 2.1 Function & Constant Locations in `App.tsx`
| Line Range | Identifier | Type | Role | Target Destination |
|---|---|---|---|---|
| **61–71** | `pages` | Constant tuple | Tab definitions & icons | `src/lib/constants.ts` |
| **72–81** | `interventionNames` | Constant Record | Human names for 8 interventions | `src/lib/constants.ts` |
| **82–95** | `Notice` | Component | System notice banner (info/error) | `src/components/common/Notice.tsx` |
| **96–103** | `Pending` | Component | Animated loading spinner | `src/components/common/Pending.tsx` |
| **104–112** | `Badge` | Component | Tone-colored badge indicator | `src/components/common/Badge.tsx` |
| **113–140** | `Card` | Component | Container card with header & actions | `src/components/common/Card.tsx` |
| **141–164** | `Metric` | Component | KPI metric card with icon & tone | `src/components/common/MetricCard.tsx` |
| **165–185** | `ZonePicker` | Component | Analysis zone select dropdown | `src/components/zone/ZonePicker.tsx` |
| **186–536** | `App` | Root Component | Monolithic state, layout, router, modal | `src/App.tsx` (Slim orchestrator) |
| **537–719** | `Overview` | Page Component | City KPI grid, map preview, insights | `src/pages/OverviewPage.tsx` |
| **720–774** | `ZoneTable` | Subcomponent | Zone priority table with badges | `src/components/zone/ZoneTable.tsx` |
| **775–823** | `Importance` | Subcomponent | Recharts vertical SHAP bar chart | `src/components/charts/ImportanceBarChart.tsx` |
| **824–879** | `ZoneDetails` | Subcomponent | Zone thermal, vegetation, risk card | `src/components/zone/ZoneDetails.tsx` |
| **880–1019** | `Prediction` | Page Component | Model cards, scatter plot, spatial split | `src/pages/PredictionsPage.tsx` |
| **1020–1086** | `Explain` | Page Component | Global & local SHAP explanations, map | `src/pages/ExplainPage.tsx` |
| **1087–1202** | `Risk` | Page Component | Risk formula sliders, searchable table | `src/pages/RiskPage.tsx` |
| **1203–1425** | `Simulator` | Page Component | 8 intervention sliders, feasibility check | `src/pages/SimulatorPage.tsx` |
| **1426–1638** | `Optimizer` | Page Component | CP-SAT optimizer, allocations table | `src/pages/OptimizerPage.tsx` |
| **1639–1785** | `Assistant` | Page Component | Grounded AI chat with citations | `src/pages/AssistantPage.tsx` |
| **1786–1942** | `Reports` | Page Component | Report generation, downloads, provenance | `src/pages/ReportsPage.tsx` |
| **1943–2164** | `DataDialog` | Modal Component | Data ingestion form & coverage catalog | `src/components/modals/DataDialog.tsx` |
| **N/A (NEW)** | `ZoneCompare` | Page Component | Multi-zone side-by-side comparison | `src/pages/ZoneComparePage.tsx` |

---

## 3. Delineation of the 10 Page Boundaries

### 3.1 `OverviewPage` (`src/pages/OverviewPage.tsx`)
- **App.tsx Lines:** 537–719 (`function Overview`)
- **Render Call in App:** Lines 429–436
- **Subcomponents Used:**
  - `MetricCard` (extracted from lines 141–164)
  - `HeatMap` (`src/components/HeatMap.tsx`)
  - `ZoneTable` (extracted from lines 720–774)
  - `ImportanceBarChart` (extracted from lines 775–823)
  - `Badge`, `Card`, `Notice`
- **Internal State:** None (fully controlled via props).
- **Queries/Mutations:** Relies on parent-provided `overview` and `map` queries.
- **Props Specification:**
  ```typescript
  export interface OverviewPageProps {
    city: string;
    overview: CityOverview;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
    layer: string;
    onLayer: (layer: string) => void;
    navigate: (page: string) => void;
  }
  ```
- **Sections Rendered:**
  1. Top `metrics-grid`: 4 KPI cards (Area Analyzed, Average Surface Heat, Heat Hotspots, Population in high-risk zones).
  2. `overview-main`:
     - Card "The city's heat landscape" with `HeatMap` preview + "Explore map" text-button navigating to Map page. Footer with high-risk zone count and coordinate system label.
     - `insight-column`:
       - `insight-card` "FROM THE EVIDENCE": Top feature driver badge, landscape point, focus point, button navigating to Explainable AI.
       - `next-action` Card: Quick jump button to Intervention Simulator.
  3. `overview-bottom`:
     - Card "Priority zones" with `ZoneTable` showing top 5 priority zones; clicking a zone sets `selected` and navigates to Map page. Action button links to Heat Risk page.
     - Card "What's driving surface heat?" with `ImportanceBarChart` showing top 5 global features and link to Explainable AI.
  4. Bottom `Notice` clarifying synthetic data demonstration.

---

### 3.2 `MapPage` (`src/pages/MapPage.tsx`)
- **App.tsx Lines:** 437–450 (`<div className="map-page">`) + `ZoneDetails` (824–879)
- **Subcomponents Used:**
  - `HeatMap` (`src/components/HeatMap.tsx`)
  - `ZoneDetails` (`src/components/zone/ZoneDetails.tsx`)
  - `Card`, `Button`, `Badge`
- **Internal State:** None.
- **Props Specification:**
  ```typescript
  export interface MapPageProps {
    city: string;
    data: ZoneFeatureCollection;
    overview?: CityOverview;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
    layer: string;
    onLayer: (layer: string) => void;
    navigate: (page: string) => void;
  }
  ```
- **Sections Rendered:**
  1. Full-height Leaflet choropleth map (`HeatMap` with `tall=true`). Allows switching among 8 choropleth layers: `predicted_suhii`, `risk_score`, `ndvi`, `building_density`, `population_density`, `shap_ndvi`, `shap_ndbi`, `shap_building_density`.
  2. `ZoneDetails` side panel: Displays selected zone name, protected status badge, predicted SUHII (°C), residual-calibrated range, predicted LST, rural reference LST, NDVI, building density %, synthetic population, risk score / 100, spatial partition, and button "Test an intervention" jumping to Simulator.

---

### 3.3 `PredictionsPage` (`src/pages/PredictionsPage.tsx`)
- **App.tsx Lines:** 880–1019 (`function Prediction`)
- **Render Call in App:** Line 452 (`<Prediction key={city} {...common} />`)
- **Subcomponents Used:**
  - `Card`, `Badge`, `Button`, `Notice`
  - Recharts `ResponsiveContainer`, `ScatterChart`, `Scatter`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip`, `ReferenceLine`
  - `WeatherTimeSeriesChart` (`src/components/charts/WeatherTimeSeriesChart.tsx`) — **integrated to resolve orphaned `/data/series` query and complete Feature 5!**
- **Internal State & Queries:**
  - `useQueryClient()`
  - `useQuery({ queryKey: ["series"], queryFn: () => getSeries() })` (Open-Meteo series)
  - `useMutation({ mutationFn: () => trainModels(city), onSuccess: () => { invalidateQueries... } })`
- **Props Specification:**
  ```typescript
  export interface PredictionsPageProps {
    city: string;
    data: ZoneFeatureCollection;
    overview: CityOverview;
    notify: (message: string) => void;
  }
  ```
- **Sections Rendered:**
  1. `section-toolbar`: Notice on held-out synthetic evaluation + "Retrain models" button with spinning icon during mutation.
  2. Retrain error alert if mutation fails.
  3. `model-cards`: 3 model evaluation cards (Random Forest, XGBoost, LightGBM) displaying test $R^2$, RMSE, MAE, Validation RMSE, with "Selected" badge for winner and "Compared" for others.
  4. `two-columns`:
     - Left Card "Observed label vs. prediction": Scatter plot of synthetic SUHII label vs model prediction on held-out spatial test partition, with 1:1 diagonal dashed reference line.
     - Right Card "A spatially separated evaluation": Spatial split ratios bar graphic (`training`, `validation`, `buffer`, `test`), spatial blocking method description, empirical uncertainty interval ($\pm 90$th percentile absolute residual), surface-heat trend note, and model selection rule.
  5. Weather Time-Series Visualization (Feature 5): Render `WeatherTimeSeriesChart` beneath the split cards, displaying daily temperature (°C) and humidity (%) trends from `/data/series`.

---

### 3.4 `ExplainPage` (`src/pages/ExplainPage.tsx`)
- **App.tsx Lines:** 1020–1086 (`function Explain`)
- **Render Call in App:** Line 454 (`<Explain key={city} {...common} />`)
- **Subcomponents Used:**
  - `ZonePicker` (`src/components/zone/ZonePicker.tsx`)
  - `ImportanceBarChart` (`src/components/charts/ImportanceBarChart.tsx`)
  - `HeatMap` (`src/components/HeatMap.tsx`)
  - `Card`, `Notice`, `Pending`
- **Internal State & Queries:**
  - `useQuery({ queryKey: ["explain", city, selected.id], queryFn: () => getExplanation(city, selected.id) })`
- **Props Specification:**
  ```typescript
  export interface ExplainPageProps {
    city: string;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
    overview: CityOverview;
  }
  ```
- **Sections Rendered:**
  1. `section-toolbar`: Note regarding actual TreeSHAP values from winner model + `ZonePicker` dropdown.
  2. `two-columns`:
     - Left Card "Global feature importance": Mean absolute SHAP bar chart across all grid cells.
     - Right Card "Why this zone?": Local SHAP contributions for the selected zone (colored green for negative/cooling contributions, teal for positive/heating contributions), plus exact additive equation: `Base {base_value}°C + contributions = {prediction}°C`.
  3. Card "How vegetation's contribution varies": Leaflet map locked to the `shap_ndvi` spatial layer.
  4. Bottom Notice clarifying that SHAP reflects statistical associations, not causal intervention cooling.

---

### 3.5 `RiskPage` (`src/pages/RiskPage.tsx`)
- **App.tsx Lines:** 1087–1202 (`function Risk`)
- **Render Call in App:** Line 455 (`<Risk key={city} {...common} />`)
- **Subcomponents Used:**
  - `ZoneTable` (`src/components/zone/ZoneTable.tsx`)
  - `Card`, `Button`, `Notice`
- **Internal State & Mutations:**
  - `const [weights, setWeights] = useState<[number, number, number]>([1, 1, 1])`
  - `const [query, setQuery] = useState("")`
  - `useMutation({ mutationFn: () => analyzeRisk(city, weights[0], weights[1], weights[2]) })`
- **Props Specification:**
  ```typescript
  export interface RiskPageProps {
    city: string;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
  }
  ```
- **Sections Rendered:**
  1. `two-columns risk-layout`:
     - Left Card "Make priorities explicit": Risk framework formula ($Risk = Hazard^{w_H} \times Exposure^{w_E} \times Vulnerability^{w_V}$), 3 range sliders for Hazard, Exposure, Vulnerability (0.1 to 3.0, step 0.1), and "Recalculate priorities" Button.
     - Right Card "What the score can tell you": Breakdown of Hazard (SUHII / 8), Exposure (pop density / 25k), Vulnerability (elderly share / 25%), scaling explanation, and demographic limitations notice.
  2. Card "Zone priorities": Search box filtering by zone name, `ZoneTable` displaying top 40 sorted zones with live or recalculated risk scores.
  3. Bottom selected zone summary indicator.

---

### 3.6 `SimulatorPage` (`src/pages/SimulatorPage.tsx`)
- **App.tsx Lines:** 1203–1425 (`function Simulator`)
- **Render Call in App:** Lines 456–458 (`<Simulator key={city} {...common} />`)
- **Subcomponents Used:**
  - `ZonePicker` (`src/components/zone/ZonePicker.tsx`)
  - `Card`, `Button`, `Badge`, `Notice`, `Pending`
- **Internal State & Queries/Mutations:**
  - `const [coverage, setCoverage] = useState<Record<string, number>>({ trees: 5, cool_roofs: 10 })`
  - `const [name, setName] = useState("Greener streets")`
  - `const [water, setWater] = useState(1000)`
  - `useQuery({ queryKey: ["scenarios", city], queryFn: () => getScenarios(city) })`
  - `useMutation({ mutationFn: () => runSimulation(...), onSuccess: () => { invalidateQueries... } })`
- **Props Specification:**
  ```typescript
  export interface SimulatorPageProps {
    city: string;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
    notify: (message: string) => void;
  }
  ```
- **Sections Rendered:**
  1. `section-toolbar`: Sensitivity range notice ($\pm 40\%$) + `ZonePicker`.
  2. `sim-layout`:
     - Left Card "Design your scenario": Name input, zone physical constraints summary (Available Land %, Roofs %, Roads %), 8 intervention range sliders (0–60%, step 5%), daily water input (m³/day), and "Run & save scenario" Button.
     - Right Stack:
       - Card "Before & after": Shows Current SUHII vs Scenario SUHII with arrow, cooling impact (°C), sensitivity range, water consumption when feasible, or list of constraint violations when infeasible.
       - Card "Scenario comparison": Table of saved simulation runs for the current city with cooling and feasibility badges.
       - Constraint rules notice (ground sharing, mutual exclusivity, protected status).

---

### 3.7 `OptimizerPage` (`src/pages/OptimizerPage.tsx`)
- **App.tsx Lines:** 1426–1638 (`function Optimizer`)
- **Render Call in App:** Line 459 (`<Optimizer key={city} {...common} />`)
- **Subcomponents Used:**
  - `Card`, `Button`, `Badge`, `Notice`, `Pending`
- **Internal State & Mutations:**
  - `const [water, setWater] = useState(1000)`
  - `const [vegetation, setVegetation] = useState(40)`
  - `const [land, setLand] = useState(100)`
  - `const [minimum, setMinimum] = useState(0)`
  - `useMutation({ mutationFn: () => runOptimization(...), onSuccess: () => notify(...) })`
- **Props Specification:**
  ```typescript
  export interface OptimizerPageProps {
    city: string;
    overview: CityOverview;
    notify: (message: string) => void;
  }
  ```
- **Sections Rendered:**
  1. `sim-layout`:
     - Left Card "Set the boundaries": Water limit input, maximum added vegetation slider (0–60%), ground area utilization slider (0–100%), minimum mean surface cooling input, list of the top 5 priority zones targeted, and "Optimize interventions" Button.
     - Right Stack:
       - Card "Your intervention plan": Feasibility status badge, water used vs available, plan metrics (mean cooling, population in selected zones), allocation table by zone (Zone, Interventions & Coverage, Cooling), model explanation.
       - Card "An alternative with less water": Renders 50% water sensitivity scenario metrics when available.
       - Planning proxy notice.

---

### 3.8 `AssistantPage` (`src/pages/AssistantPage.tsx`)
- **App.tsx Lines:** 1639–1785 (`function Assistant`)
- **Render Call in App:** Line 460 (`<Assistant {...common} key={city} />`)
- **Subcomponents Used:**
  - `ZonePicker` (`src/components/zone/ZonePicker.tsx`)
  - `ZoneDetails` (`src/components/zone/ZoneDetails.tsx`)
  - `Card`, `Button`, `Badge`, `Notice`, `Pending`
- **Internal State & Mutations:**
  - `const [message, setMessage] = useState("")`
  - `const [provider, setProvider] = useState<"auto" | "groq" | "gemini" | "local">("auto")`
  - `const [messages, setMessages] = useState<ChatMessage[]>(defaultWelcomeMessages)`
  - `useMutation({ mutationFn: (q: string) => sendChatMessage(city, selected.id, q, provider) })`
- **Props Specification:**
  ```typescript
  export interface AssistantPageProps {
    city: string;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
  }
  ```
- **Sections Rendered:**
  1. `section-toolbar`: `ZonePicker` dropdown + Provider select dropdown (`auto`, `groq`, `gemini`, `local`).
  2. `chat-layout`:
     - Left Card `chat-card`:
       - Welcome state with suggested prompt buttons if empty.
       - Message bubble stream: User message vs Assistant message (with provider badge, template fallback badge, summary, factual statements with citation pills, action recommendation tags, and collapsible limitations/failures inspector).
       - Chat input form with submit button.
       - Grounding disclaimer footer.
     - Right Panel: `ZoneDetails` card for the selected zone context.

---

### 3.9 `ReportsPage` (`src/pages/ReportsPage.tsx`)
- **App.tsx Lines:** 1786–1942 (`function Reports`)
- **Render Call in App:** Lines 461–463 (`<Reports {...common} status={status.data} />`)
- **Subcomponents Used:**
  - `Card`, `Button`, `Badge`, `Notice`
- **Internal State & Mutations:**
  - `const [report, setReport] = useState<ReportResponse | undefined>()`
  - `useMutation({ mutationFn: () => generateReport(city), onSuccess: (r) => setReport(r) })`
- **Props Specification:**
  ```typescript
  export interface ReportsPageProps {
    city: string;
    overview: CityOverview;
    status?: DataStatus;
    notify: (message: string) => void;
  }
  ```
- **Sections Rendered:**
  1. `report-banner`: Banner with action button "Generate analysis report" and visual graphic card.
  2. `download-grid`: When report is generated, displays 3 download cards:
     - Markdown (`heatwise-report.md`)
     - Zone-level CSV (`heatwise-report.csv`)
     - Complete JSON (`heatwise-report.json`)
  3. `two-columns`:
     - Left Card "Methodology & provenance": Core methodology definitions (SUHII, dataset, models, simulation, optimization).
     - Right Card "Connection status": Live badges for Database engine, Groq API, Gemini API, and Google Earth Engine credentials.

---

### 3.10 `ZoneComparePage` (`src/pages/ZoneComparePage.tsx`) — NEW FEATURE
- **Status:** New dedicated page fulfilling **Feature 4 (Zone Comparison View)**.
- **Subcomponents Used:**
  - `ZoneComparisonChart` (`src/components/charts/ZoneComparisonChart.tsx`)
  - `Badge`, `Button`, `Card`, `Notice`
- **Internal State:**
  - `const [comparedIds, setComparedIds] = useState<string[]>([])` (supports up to 4 zones)
  - `const [metricTab, setMetricTab] = useState<"thermal" | "land" | "demographic" | "interventions">("thermal")`
- **Props Specification:**
  ```typescript
  export interface ZoneComparePageProps {
    city: string;
    data: ZoneFeatureCollection;
    selected: ZoneProperties;
    onSelect: (zone: ZoneProperties) => void;
    navigate: (page: string) => void;
    notify: (message: string) => void;
  }
  ```
- **Sections Rendered:**
  1. `section-toolbar`: Zone multi-selector dropdown / pills allowing planners to add or remove up to 4 zones for comparison.
  2. Metric comparison cards:
     - Top Grouped Recharts Bar Chart (`ZoneComparisonChart`) comparing:
       - Predicted SUHII (°C)
       - Risk Score (/100)
       - NDVI ($\times 100$)
       - Population Density (k people/km²)
  3. Side-by-side comparison matrix table:
     - Rows:
       - **Thermal**: Predicted SUHII, Predicted LST, Rural Reference LST, Residual Range.
       - **Landscape & Morphology**: NDVI, NDBI, Building Density, Land Cover.
       - **Vulnerability & Population**: Total Population, Elderly Share, Risk Score, Risk Classification.
       - **Intervention Capacity**: Available Land %, Roof %, Road %, Protected Status.
  4. Quick Actions: Button on each compared zone to "Open in Map" or "Simulate Interventions".

---

## 4. Routing Architecture Specification

### 4.1 Routing Strategy Evaluation: Hash vs Path Routing
| Criteria | Browser History Path (`/map`) | Hash Routing (`#/map`) | Recommendation |
|---|---|---|---|
| **Vite Dev Server** | Requires history fallback proxy | Works out of the box | **Hash Routing** |
| **Production Static Hosting** | Requires server rewrite rules (nginx/caddy/s3) | 100% server-agnostic, zero 404s on reload | **Hash Routing** |
| **FastAPI Backend Proxy** | Requires SPA catch-all route `/{path:path}` | Root `/` serves `index.html`, hash is client-only | **Hash Routing** |
| **Dependencies** | Requires `react-router-dom` (adds weight, risk with React 19) | Zero dependencies (custom lightweight hook) | **Hash Routing** |
| **Browser History** | Supported | Fully supported (`popstate` / `hashchange`) | **Hash Routing** |
| **URL Deep Linking** | `domain.com/map?city=Delhi` | `domain.com/#/map?city=Delhi&zone=DEL_01` | **Hash Routing** |

**Decision:** Adopt **Clean Hash Routing with URL Synchronicity and Browser History Support**. It requires zero external dependencies, never causes 404 errors when reloading static builds, and supports full deep linking and browser back/forward navigation.

---

### 4.2 URL Schema & Page Mapping
The URL hash schema follows:
```
#/<page-slug>?city=<city>&zone=<zoneId>&layer=<layer>
```

#### Page Slugs & Display Titles:
| Internal Slug | Display Page Title | Route Example |
|---|---|---|
| `overview` | `Overview` | `/#/overview?city=Ahmedabad` |
| `map` | `Heat map` | `/#/map?city=Delhi&zone=DEL_02&layer=ndvi` |
| `prediction` | `AI prediction` | `/#/prediction?city=Hyderabad` |
| `explain` | `Explainable AI` | `/#/explain?city=Ahmedabad&zone=AHM_05` |
| `risk` | `Heat risk` | `/#/risk?city=Delhi` |
| `simulator` | `Intervention simulator` | `/#/simulator?city=Hyderabad&zone=HYD_01` |
| `optimizer` | `Optimization` | `/#/optimizer?city=Ahmedabad` |
| `assistant` | `AI assistant` | `/#/assistant?city=Delhi&zone=DEL_04` |
| `reports` | `Reports` | `/#/reports?city=Hyderabad` |
| `compare` | `Zone comparison` | `/#/compare?city=Ahmedabad` |

---

### 4.3 `useHashRouter` Custom Hook Design
Located at `frontend/src/hooks/useHashRouter.ts`:

```typescript
import { useState, useEffect, useCallback } from "react";
import { PageSlug, RouteState, NavigationOptions } from "../types/routes";
import { PAGE_MAP, DEFAULT_ROUTE } from "../lib/constants";

export function useHashRouter() {
  const parseHash = (): RouteState => {
    if (typeof window === "undefined") return DEFAULT_ROUTE;
    const raw = window.location.hash.replace(/^#\/?/, "");
    const [pathPart, queryPart] = raw.split("?");
    const slug = (pathPart || "overview").toLowerCase() as PageSlug;
    const page = PAGE_MAP[slug]?.slug || "overview";
    const params = new URLSearchParams(queryPart || "");
    return {
      page,
      city: params.get("city") || "Ahmedabad",
      zoneId: params.get("zone") || "",
      layer: params.get("layer") || "predicted_suhii",
    };
  };

  const [route, setRoute] = useState<RouteState>(parseHash);

  useEffect(() => {
    const handleHashChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback((target: string | NavigationOptions) => {
    let next: RouteState;
    if (typeof target === "string") {
      const slug = PAGE_MAP[target]?.slug || "overview";
      next = { ...route, page: slug };
    } else {
      next = {
        page: (target.page ? PAGE_MAP[target.page]?.slug : route.page) || route.page,
        city: target.city ?? route.city,
        zoneId: target.zoneId ?? route.zoneId,
        layer: target.layer ?? route.layer,
      };
    }
    const params = new URLSearchParams();
    if (next.city && next.city !== "Ahmedabad") params.set("city", next.city);
    if (next.zoneId) params.set("zone", next.zoneId);
    if (next.layer && next.layer !== "predicted_suhii") params.set("layer", next.layer);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    const newHash = `#/${next.page}${queryString}`;

    if (window.location.hash !== newHash) {
      if (typeof target === "object" && target.replace) {
        window.history.replaceState(null, "", newHash);
        setRoute(next);
      } else {
        window.location.hash = newHash;
      }
    }
  }, [route]);

  const setCity = useCallback((city: string) => navigate({ city, zoneId: "" }), [navigate]);
  const setZoneId = useCallback((zoneId: string) => navigate({ zoneId }), [navigate]);
  const setLayer = useCallback((layer: string) => navigate({ layer }), [navigate]);

  return { route, navigate, setCity, setZoneId, setLayer };
}
```

---

## 5. Slimmed-Down `App.tsx` Orchestrator (<150 Lines)

By extracting layout components, modals, and page views, `App.tsx` becomes a concise, declarative orchestrator of **under 135 lines**:

```tsx
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useHashRouter } from "./hooks/useHashRouter";
import { getOverview, getMap } from "./services/heatService";
import { getDataStatus } from "./services/dataService";
import { generateReport } from "./services/reportService";
import { download } from "./lib/utils";
import { PAGE_TITLE_MAP } from "./lib/constants";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import PageHeader from "./components/layout/PageHeader";
import ContextBar from "./components/layout/ContextBar";
import Footer from "./components/layout/Footer";
import DataDialog from "./components/modals/DataDialog";
import SettingsModal from "./components/modals/SettingsModal";
import Notice from "./components/common/Notice";
import Pending from "./components/common/Pending";
import Toast from "./components/common/Toast";
import OverviewPage from "./pages/OverviewPage";
import MapPage from "./pages/MapPage";
import PredictionsPage from "./pages/PredictionsPage";
import ExplainPage from "./pages/ExplainPage";
import RiskPage from "./pages/RiskPage";
import SimulatorPage from "./pages/SimulatorPage";
import OptimizerPage from "./pages/OptimizerPage";
import AssistantPage from "./pages/AssistantPage";
import ReportsPage from "./pages/ReportsPage";
import ZoneComparePage from "./pages/ZoneComparePage";
import type { ZoneProperties } from "./types/geojson";

export default function App() {
  const { route, navigate, setCity, setZoneId, setLayer } = useHashRouter();
  const [drawer, setDrawer] = useState(false);
  const [dataOpen, setDataOpen] = useState(false);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [toast, setToast] = useState("");

  const { city, page, layer, zoneId } = route;
  const overview = useQuery({ queryKey: ["overview", city], queryFn: () => getOverview(city) });
  const map = useQuery({ queryKey: ["map", city], queryFn: () => getMap(city) });
  const status = useQuery({ queryKey: ["status"], queryFn: () => getDataStatus() });

  const selected = map.data?.features.find(f => f.properties.id === zoneId)?.properties
    || overview.data?.priority_zones[0];

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 5000); };

  const exportReport = useMutation({
    mutationFn: () => generateReport(city),
    onSuccess: async (r) => {
      try {
        await download(r.markdown_url, "heatwise-report.md");
        notify("Analysis report downloaded.");
      } catch (e: any) { notify(e.message); }
    },
  });

  const commonProps = {
    city,
    data: map.data!,
    overview: overview.data!,
    selected: selected!,
    onSelect: (p: ZoneProperties) => setZoneId(p.id),
    notify,
  };

  const pageTitle = PAGE_TITLE_MAP[page] || "Overview";

  return (
    <div className="app">
      <Sidebar
        page={pageTitle}
        onNavigate={(p) => { navigate(p); setDrawer(false); }}
        isOpen={drawer}
        onOpenData={() => setDataOpen(true)}
        onOpenSettings={() => setTokenOpen(true)}
      />
      {drawer && <button className="scrim" aria-label="Close navigation" onClick={() => setDrawer(false)} />}
      <div className="main">
        <Topbar pageTitle={pageTitle} onOpenDrawer={() => setDrawer(true)} onNavigate={navigate} />
        <main>
          <PageHeader
            pageTitle={pageTitle}
            city={city}
            onCityChange={setCity}
            onExportReport={() => exportReport.mutate()}
            isExporting={exportReport.isPending}
          />
          <ContextBar onOpenData={() => setDataOpen(true)} />
          {(overview.isError || map.isError) && (
            <Notice error>
              {(overview.error || map.error)?.message}
              <button className="btn btn-outline" onClick={() => { overview.refetch(); map.refetch(); }}>Retry</button>
            </Notice>
          )}
          {overview.isPending || map.isPending ? (
            <Pending />
          ) : overview.data && map.data && selected ? (
            <>
              {page === "overview" && <OverviewPage {...commonProps} layer={layer} onLayer={setLayer} navigate={navigate} />}
              {page === "map" && <MapPage {...commonProps} layer={layer} onLayer={setLayer} navigate={navigate} />}
              {page === "prediction" && <PredictionsPage key={city} {...commonProps} />}
              {page === "explain" && <ExplainPage key={city} {...commonProps} />}
              {page === "risk" && <RiskPage key={city} {...commonProps} />}
              {page === "simulator" && <SimulatorPage key={city} {...commonProps} />}
              {page === "optimizer" && <OptimizerPage key={city} {...commonProps} />}
              {page === "assistant" && <AssistantPage key={city} {...commonProps} />}
              {page === "reports" && <ReportsPage {...commonProps} status={status.data} />}
              {page === "compare" && <ZoneComparePage key={city} {...commonProps} navigate={navigate} />}
            </>
          ) : null}
          <Footer />
        </main>
      </div>
      {dataOpen && <DataDialog city={city} close={() => setDataOpen(false)} notify={notify} />}
      {tokenOpen && <SettingsModal close={() => setTokenOpen(false)} />}
      {(toast || exportReport.isError) && (
        <Toast message={toast || exportReport.error?.message || ""} onClose={() => { setToast(""); exportReport.reset(); }} />
      )}
    </div>
  );
}
```

---

## 6. Directory Structure & File Specifications

```
frontend/src/
├── types/
│   ├── index.ts                     # Barrel exports for all domain types
│   ├── geojson.ts                   # ZoneProperties, ZoneFeature, ZoneFeatureCollection
│   ├── overview.ts                  # CityOverview, PriorityZone, FeatureImportance
│   ├── ml.ts                        # ModelEvaluation, SplitGraphic, TreeSHAP
│   ├── simulation.ts                # Interventions, Constraints, Scenarios
│   ├── optimization.ts              # CP-SAT request/response, Selections
│   ├── weather.ts                   # WeatherPoint, WeatherSeries, WeatherSeriesResponse
│   ├── chat.ts                      # ChatMessage, AIFinding, ChatFact
│   ├── data.ts                      # IngestPayload, DataStatus, CatalogItem
│   └── routes.ts                    # PageSlug, RouteState, NavigationOptions
│
├── lib/
│   ├── constants.ts                 # PAGES, PAGE_MAP, INTERVENTIONS, CITIES, COLORS
│   └── utils.ts                     # cn, fmt, label, download
│
├── services/
│   ├── api.ts                       # Strongly typed api fetch wrapper
│   ├── heatService.ts               # getOverview, getMap, getHotspots
│   ├── mlService.ts                 # trainModels, getExplanation
│   ├── simulationService.ts         # runSimulation, getScenarios
│   ├── optimizationService.ts       # runOptimization
│   ├── dataService.ts               # getDataStatus, getSeries, ingestData
│   ├── chatService.ts               # sendChatMessage
│   └── reportService.ts             # generateReport
│
├── hooks/
│   ├── useHashRouter.ts             # Clean hash routing & URL synchronicity
│   └── useZoneComparison.ts         # Multi-zone comparison selection state
│
├── components/
│   ├── common/
│   │   ├── Badge.tsx                # Status / tone indicator
│   │   ├── Button.tsx               # CVA Button primitive
│   │   ├── Card.tsx                 # Standard content card
│   │   ├── MetricCard.tsx           # KPI metric card
│   │   ├── Notice.tsx               # Warning / notice banner
│   │   ├── Pending.tsx              # Loading spinner
│   │   └── Toast.tsx                # Floating notification toast
│   │
│   ├── layout/
│   │   ├── Sidebar.tsx              # Left navigation sidebar
│   │   ├── Topbar.tsx               # Header with breadcrumbs & actions
│   │   ├── PageHeader.tsx           # Page title, city switcher, export button
│   │   ├── ContextBar.tsx           # Data status & provenance indicator
│   │   └── Footer.tsx               # Bottom disclaimer
│   │
│   ├── zone/
│   │   ├── ZonePicker.tsx           # Single zone select dropdown
│   │   ├── ZoneTable.tsx            # Priority ranking table
│   │   └── ZoneDetails.tsx          # Zone metric card
│   │
│   ├── map/
│   │   ├── HeatMap.tsx              # Leaflet choropleth map
│   │   └── BoundarySketch.tsx       # Leaflet polygon sketcher (re-integrated!)
│   │
│   ├── charts/
│   │   ├── ImportanceBarChart.tsx   # SHAP feature importance vertical bar chart
│   │   ├── WeatherTimeSeriesChart.tsx # Recharts LineChart for weather series (NEW)
│   │   └── ZoneComparisonChart.tsx  # Multi-zone comparative bar chart (NEW)
│   │
│   └── modals/
│       ├── DataDialog.tsx           # Ingestion modal with BoundarySketch toggle
│       └── SettingsModal.tsx        # Session token manager
│
├── pages/
│   ├── OverviewPage.tsx             # 1. City summary & KPI metrics
│   ├── MapPage.tsx                  # 2. Choropleth map & zone details
│   ├── PredictionsPage.tsx          # 3. Model tournament & weather series
│   ├── ExplainPage.tsx              # 4. TreeSHAP feature explanations
│   ├── RiskPage.tsx                 # 5. Risk formula & priority rankings
│   ├── SimulatorPage.tsx            # 6. Physical cooling intervention simulator
│   ├── OptimizerPage.tsx            # 7. CP-SAT multi-zone optimizer
│   ├── AssistantPage.tsx            # 8. Grounded AI chat assistant
│   ├── ReportsPage.tsx              # 9. Reproducible report downloads
│   └── ZoneComparePage.tsx          # 10. Multi-zone comparison view (NEW)
│
├── tests/
│   ├── utils.test.ts                # Unit tests for formatters and helpers
│   ├── Button.test.tsx              # Component test for Button
│   ├── Badge.test.tsx               # Component test for Badge
│   ├── MetricCard.test.tsx          # Component test for MetricCard
│   ├── ZoneTable.test.tsx           # Component test for ZoneTable
│   └── router.test.ts               # Unit test for useHashRouter logic
│
└── App.tsx                          # Slim orchestrator (<150 lines)
```

---

## 7. Modal & BoundarySketch Integration (Feature 6)

In `src/components/modals/DataDialog.tsx`, activate `BoundarySketch.tsx`:
```tsx
const [sketchMode, setSketchMode] = useState<"draw" | "manual">("draw");

// When source is "earth_engine" or "sample":
<div className="boundary-input-group">
  <div className="sketch-tab-bar">
    <button
      type="button"
      className={sketchMode === "draw" ? "active" : ""}
      onClick={() => setSketchMode("draw")}
    >
      Draw Boundary on Map
    </button>
    <button
      type="button"
      className={sketchMode === "manual" ? "active" : ""}
      onClick={() => setSketchMode("manual")}
    >
      Paste GeoJSON
    </button>
  </div>
  {sketchMode === "draw" ? (
    <BoundarySketch city={city} onChange={(json) => setBoundary(json)} />
  ) : (
    <textarea
      value={boundary}
      onChange={(e) => setBoundary(e.target.value)}
      rows={3}
      placeholder='{"type":"Polygon","coordinates":[...]}'
    />
  )}
</div>
```
This re-activates the 117-line `BoundarySketch.tsx` component, eliminates dead code, and provides visual boundary polygon drawing.

---

## 8. Implementation Recommendations for the Worker

The implementer should execute in 4 discrete steps:

1. **Step 1: Domain Types & Services Setup**
   - Create all TypeScript definition files in `src/types/`.
   - Break `api.ts` into modular, typed clients in `src/services/`.
   - Create `src/lib/constants.ts` and `src/lib/utils.ts`.

2. **Step 2: Common, Layout, & Zone Components**
   - Extract primitives into `src/components/common/`.
   - Extract `Sidebar`, `Topbar`, `PageHeader`, `ContextBar`, `Footer` into `src/components/layout/`.
   - Extract `ZonePicker`, `ZoneTable`, `ZoneDetails` into `src/components/zone/`.
   - Build `WeatherTimeSeriesChart` and `ZoneComparisonChart` in `src/components/charts/`.
   - Extract `DataDialog` and `SettingsModal` into `src/components/modals/` with `BoundarySketch` wired in.

3. **Step 3: Hash Router & 10 Page Modules**
   - Implement `src/hooks/useHashRouter.ts`.
   - Create the 10 page components in `src/pages/`.
   - Rewrite `src/App.tsx` using the slim orchestrator template (<150 lines).

4. **Step 4: Vitest Configuration & Tests**
   - Add happy-dom/jsdom setup to `vite.config.ts`.
   - Add unit tests in `src/tests/` to satisfy `npm test`.
   - Verify `npm run build` generates clean chunks with zero TypeScript errors.
