# Frontend Architecture & Service Integrations

This document describes the frontend implementation for the Urban Heat Resilience platform (HeatWise), detailing the revised backend service integration, synthetic-data detection and warning badges, geospatial raster sidecar viewer linkage, and the test suite.

---

## 1. Revised Backend Endpoints & API Client Services

All API service clients under `frontend/src/services/` have been revised to route to standard `/api/...` endpoints and conform to the backend contracts:

### Summary of Endpoint Revisions
| Service | Method | Route | Description / Invariants |
|---|---|---|---|
| `heatService.predictZone` | POST | `/api/heat/predict` | Predicts single-zone or city-wide SUHII and uncertainty intervals. Accepts `{ city, zone_id }`. |
| `aiService.chat` | POST | `/api/ai/chat` | Context-aware AI resilience assistant reasoning grounded against spatial facts, simulations, and optimizations. |
| `optimizationService.runOptimization` | POST | `/api/optimization/run` | Discrete OR-Tools CP-SAT multi-zone optimizer. **Strictly strips all budget fields (`budget_limit`, `budget_enforced`)** prior to transmission. |
| `dataService.getDataSeries` / `weatherService.getWeatherSeries` | GET | `/api/data/series` | Returns hourly air temperature, relative humidity, and meteorological time-series records. |
| `heatService.getHeatMap` | GET | `/api/heat/map?city={city}` | Returns GeoJSON FeatureCollection of spatial zones with metadata. |
| `heatService.getOverview` | GET | `/api/overview?city={city}` | Returns city-wide aggregate statistics, priority risk zones, and model evaluation. |

### API Client Robustness (`frontend/src/services/apiClient.ts`)
- **Path Normalization**: Automatically resolves paths whether supplied with or without a leading `/api/` prefix (e.g., both `/api/heat/predict` and `/heat/predict` normalize cleanly to `/api/heat/predict` without path doubling).
- **Session Authentication**: Injects `Authorization: Bearer {token}` when a session token is present in `sessionStorage`.
- **Structured Error Handling**: Throws custom `ApiError` instances containing HTTP `status` and parsed JSON `details` (e.g., Pydantic validation errors from 400 responses).
- **Network & Parse Safeguards**: Network timeouts, connection drops, and malformed JSON are intercepted and mapped into structured `ApiError` instances (status 0 for network dropouts).

---

## 2. Synthetic Data Handling & Warning Component

### Warning Detection
When remote data providers (GEE, Sentinel, Landsat, WorldPop) are unavailable or fallbacks are used, the backend marks the dataset metadata with:
- `metadata.isSynthetic: true`
- `metadata.synthetic: true`
- `metadata.source: "synthetic"` or `"Seeded synthetic demonstration dataset"`

The frontend detects this condition across both boolean flags (`metadata.isSynthetic`, `metadata.synthetic`) and source strings.

### `SyntheticWarningBadge` Component (`frontend/src/components/common/SyntheticWarningBadge.tsx`)
- **Props**:
  - `metadata`: `SyntheticMetadataInput` (accepts `DatasetMetadata` or partial metadata objects).
  - `isSynthetic`: Boolean override.
  - `className`: Custom CSS classes.
  - `showIcon`: Boolean controlling warning icon visibility (default: `true`).
  - `children`: Optional custom message text (default: `"Synthetic Fallback Data"`).
- **Behavior**:
  - If a synthetic fallback dataset is detected, renders a high-visibility badge with an alert icon, `role="status"`, and `data-testid="synthetic-warning-badge"`.
  - If live/validated data is active, renders nothing (`null`), leaving the UI clean.
- **Placement**:
  - **Topbar**: Active indicator visible globally across all tabs whenever fallback data is loaded.
  - **MapPage Banner**: Contextual alert above the interactive map warning that spatial heat and risk metrics are using a synthetic fallback dataset.
  - **HeatMap Badge**: Grid indicator overlay in the map container indicating synthetic resolution status.

---

## 3. Map Page & Geospatial Raster Sidecar Viewer Integration

### SUHII Display with Proper Units
- Surface Urban Heat Island Intensity (SUHII) values are displayed consistently with standard metric units across all views:
  - Feature polygon tooltips: `${Number(predicted_suhii).toFixed(1)} °C SUHII`
  - Zone details KPI panel: `${Number(predicted_suhii).toFixed(1)}°C` and uncertainty interval `[${interval_low}, ${interval_high}]°C`
  - LST comparison: `${Number(predicted_lst).toFixed(1)}°C` against rural baseline `${rural_reference}°C`

### Raster Layer Classification & Sidecar Linking (`frontend/src/lib/raster.ts`)
- The `isRasterLayer(layerName)` utility identifies continuous surface and remote-sensing raster layers:
  - `predicted_suhii` (thermal LST surface difference)
  - `ndvi`, `ndwi`, `ndbi`, `ndbai` (optical & spectral indices)
  - `building_density`, `population_density` (continuous gridded density rasters)
  - Dynamic prefixes: `raster_*`, `sentinel_*`
- For any active raster layer, the UI surfaces a direct deep-link to the sidecar viewer:
  - **Feature Tooltip**: Interactive link in the Leaflet polygon tooltip: `Open in Sidecar Viewer ↗` (`sidecar://biomolecular_structure_viewer`).
  - **Map Layer Selector**: Direct `Sidecar Viewer` badge next to the layer dropdown when a raster layer is selected.
  - **Zone Details Panel**: Quick-action button linking directly to `sidecar://biomolecular_structure_viewer` with the selected layer.

---

## 4. Verification and Testing

### Vitest Test Suite (`frontend/src/tests/`)
- **`api.test.ts`**:
  - Path normalization tests.
  - Error handling: HTTP 400 with detail payload, HTTP 404, HTTP 500, status 0 on network disconnect, 204 No Content.
  - Contract verification for revised endpoints:
    - `/api/heat/predict` payload and response.
    - `/api/ai/chat` payload and response.
    - `/api/optimization/run` verifying `budget_limit` and `budget_enforced` are stripped.
    - `/api/data/series` verification via `dataService` and `weatherService`.
- **`syntheticWarningBadge.test.tsx`**:
  - Renders when `metadata.isSynthetic` is `true`.
  - Renders when `metadata.synthetic` is `true`.
  - Renders when `metadata.source === "synthetic"`.
  - Hides completely when `isSynthetic: false` or live data is present.
  - Custom children, class names, and icon toggles.
- **`mapPageSidecar.test.tsx`**:
  - Verification of `isRasterLayer` classification logic.
  - Verification of SUHII value formatting and `°C` units.
  - Verification of `sidecar://biomolecular_structure_viewer` link rendering for raster layers.
  - Suppression of sidecar links for non-raster layers.

---

## 5. Milestone M6: Dark-First Climate Intelligence & Geospatial Map Platform

As part of Milestone M6, the entire frontend was transformed into a dark-first climate-intelligence command center:

### 1. Dark-First Design System (`frontend/src/styles.css`)
- **Surfaces**: Obsidian deep canvas (`#080c11`), slate navigation & header (`#0e141d`), elevated cards and modals (`#121924`, `#17202e`).
- **Borders**: Precision hairline borders (`rgba(255,255,255,0.08)` to `0.12`).
- **Telemetry Typography**: Monospace numeric numerals (`JetBrains Mono`, `Fira Code`, `ui-monospace`) with tabular numerals enabled (`tnum`, `cv02`).
- **Crisp Accents**: Emerald (`#10b981`), Cyan (`#06b6d4`), Amber (`#f59e0b`), Rose (`#f43f5e`), and Violet (`#a855f7`).

### 2. Collapsible Shell & Omni-Search Command Palette
- **Collapsible Sidebar (`Sidebar.tsx`)**:
  - Expanded mode (240px) with high-visibility branding, group titles, active pills, and target city telemetry card.
  - Collapsed rail mode (64px) with centered SVG icons and hover tooltips for compact workspace mode.
  - Mobile overlay drawer with backdrop blur and touch dismiss.
- **Top Command Bar (`CommandBar.tsx` / `Topbar.tsx`)**:
  - Global `Ctrl+K` / `⌘K` command palette.
  - Fuzzy omni-search across canonical views, target cities (Ahmedabad, Delhi, Hyderabad), municipal wards, and map layers.
  - Keyboard navigation (Arrow keys, Enter, Esc).

### 3. 10 Canonical Views
1. **Overview Command Center (`OverviewPage.tsx`)**: High-level municipal heat metrics, priority wards, and EO provenance.
2. **Live Environmental Map (`MapPage.tsx`)**: CartoDB Dark Matter GIS engine with multi-layer stacking, opacity sliders, physical legends, and raster sidecar linkage.
3. **Heat Analysis (`PredictionsPage.tsx` / `HeatPage`)**: Spatial machine learning tournament (Random Forest, XGBoost, LightGBM), test residual scatter, and ward comparisons.
4. **Environmental Analysis (`EnvironmentalPage.tsx`)**: Dedicated environmental telemetry view with Open-Meteo hourly/daily charts, OpenAQ/CPCB air quality stations, and CGWB groundwater monitoring wells.
5. **Heat Risk & Vulnerability (`RiskPage.tsx`)**: Transparent Hazard × Exposure × Vulnerability decomposition.
6. **Explainable AI (`ExplainPage.tsx`)**: Additive TreeSHAP global feature importance and zone-specific attributions.
7. **Mitigation Planning (`SimulatorPage.tsx`)**: Multi-intervention scenario simulation with physical land/roof constraints.
8. **Intervention Optimization (`OptimizerPage.tsx`)**: Discrete OR-Tools CP-SAT physical combinatorial optimization (water availability, vegetation cap, land limit, min cooling — zero budget constraints).
9. **AI Climate Assistant (`AssistantPage.tsx`)**: Grounded multi-provider (Groq / Gemini) climate advisor with source citations and numeric guardrails.
10. **Reports (`ReportsPage.tsx`)**: Downloadable municipal reports in Markdown, CSV, and JSON formats.

### 4. Reusable Geospatial Multi-Layer Map (`HeatMap.tsx`)
- **CartoDB Dark Matter Basemap**: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png` with OSM fallback.
- **Multi-Layer Stacking**: Toggleable Land Surface Temperature (LST), predicted SUHII, NDVI, built-up density, population exposure, and SHAP contributions.
- **Point Overlay Stations**: Air Quality stations (OpenAQ/CPCB), Weather telemetry (Open-Meteo), and Groundwater piezometer wells (CGWB).
- **Opacity Controls**: Interactive range slider adjusting layer alpha from 20% to 95%.
- **Physical-Unit Legends**: Contextual units (`°C`, `µg/m³`, `mbgl`, `[-1, 1]`, `%`).
- **Zone Inspection**: Deep-links to `sidecar://biomolecular_structure_viewer` preserved for all continuous raster layers.

---

## 6. Running Tests and Build
```bash
# Run Vitest test suite
npm --prefix frontend test

# Run TypeScript type check and production bundle build
npm --prefix frontend run build
```
