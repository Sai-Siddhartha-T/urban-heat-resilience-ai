# Handoff Report — Survey 1: Frontend Architecture, UI/UX Redesign, Navigation & Geospatial Map

**Date**: 2026-11-10  
**From**: Teamwork Explorer (Survey 1) (`teamwork_explorer_survey_1`)  
**To**: Lead Orchestrator (`ef9393af-13d2-4069-906d-ff502c4a45d2`) & Agent 7 (Frontend, Integration, Testing and Documentation Engineer)  
**Detailed Report**: `.agents/teamwork/teamwork_explorer_survey_1/analysis.md`  

---

## 1. Observation

1. **Current Styling & Theme**:
   - `frontend/src/styles.css:15-22`:
     ```css
     :root {
       font-family: "DM Sans", sans-serif;
       color: #263d34;
       background: #f6f8f5;
       font-synthesis: none;
       font-size: 13px;
       font-weight: 400;
     }
     ```
     The frontend is completely configured in a light pastel-green palette with light background (`#f6f8f5`), olive text (`#263d34`), and light mint cards (`#eaf2e9`). There is no dark-mode token set or dark-first UI architecture.
2. **Current Application Shell**:
   - `frontend/src/components/layout/Sidebar.tsx:20-58`: Fixed-width sidebar (`width: 238px` at `styles.css:107`), no collapsed state, no icon-only mode, and no mobile overlay drawer.
   - `frontend/src/components/layout/Topbar.tsx:26-60`: Contains only a city picker button row and a data dialog button. It lacks the required top command bar (`⌘K` / `Ctrl+K` command palette, omni-search, quick actions).
3. **Current Page & Route Inventory**:
   - `frontend/src/lib/constants.ts:41-52`:
     Defines 10 pages: `overview` (Overview), `map` (Heat map), `compare` (Zone comparison), `prediction` (AI prediction), `explain` (Explainable AI), `risk` (Heat risk), `simulator` (Intervention simulator), `optimizer` (Optimization), `assistant` (AI assistant), `reports` (Reports).
   - Notably missing: A dedicated view for **Environmental Analysis** (weather observations, air quality monitoring network, groundwater trends). Weather time series was relegated to a secondary chart in `PredictionsPage.tsx:189-195`.
4. **Current Mapping System**:
   - `frontend/src/components/HeatMap.tsx:75-78`:
     Uses Leaflet `TileLayer` pointing to `/api/tiles/{z}/{x}/{y}.png` (OpenStreetMap light tiles), with container background set to `#edece2` (`styles.css:640`).
   - `HeatMap.tsx:106-122`: Layer selection is restricted to a single `<select>` dropdown (`predicted_suhii`, `risk_score`, `ndvi`, `building_density`, `population_density`, `shap_*`).
   - Missing layers: Satellite-observed Land Surface Temperature (LST), Land Cover (ESA WorldCover), Air Quality monitoring stations (OpenAQ/CPCB), Weather monitoring stations (Open-Meteo), Groundwater monitoring stations (CGWB), Population Exposure, and Proposed Mitigation Interventions.
   - Missing controls: Multi-layer stacking toggles, opacity sliders, physical-unit legends, time-period filters, and search-to-zone zooming.
5. **Existing Test & Build Results**:
   - Build command: `npm --prefix frontend run build` (`tsc -b && vite build`) completed cleanly with exit code 0, transforming 2,112 modules into `dist/assets/index-*.js` (975.79 kB) and `dist/assets/index-*.css` (64.99 kB) in 26.38s.
   - Test command: `npm --prefix frontend test` (`vitest run`) passed with exit code 0: **11 test files passed, 91 tests passed** in 10.69s.
   - Key test constraints:
     - `frontend/src/tests/mapPageSidecar.test.tsx:85-108` asserts that for raster layers (`isRasterLayer(layer) === true`), `ZoneDetails` renders `sidecar://biomolecular_structure_viewer` with `data-testid="zone-sidecar-link"`.
     - `frontend/src/tests/integration_challenge.test.ts:65-145` asserts URL hash routing, slug parsing, and query parameter persistence (`city`, `zone`, `layer`).

---

## 2. Logic Chain

1. **Requirement Compliance (R1)**:
   - *Premise*: Requirement R1 explicitly demands: *"Completely transform the existing Heatwise frontend into a premium, modern, dark-first climate-intelligence platform with Palantir-style geospatial intelligence and Linear-level interface precision. Implement an application shell with collapsible navigation and a top command bar, redesign all pages (Overview Command Center, Live Environmental Map, Heat Analysis, Environmental Analysis, Heat Risk & Vulnerability, Explainable AI, Mitigation Planning, Intervention Optimization, AI Climate Assistant, Reports)..."*
   - *Observation*: The current codebase is light-themed (Observation 1), uses a non-collapsible sidebar without a command bar (Observation 2), and lacks a dedicated Environmental Analysis page while fragmenting Heat Analysis (Observation 3).
   - *Deduction*: A complete UI redesign is required: replacing the light stylesheet with dark design tokens (obsidian `#080c11`, slate `#0e141d`, hairline borders `rgba(255,255,255,0.08)`), introducing a collapsible sidebar + top command palette (`Ctrl+K`), and organizing navigation into the 10 canonical views.
2. **Geospatial Platform Compliance (R4)**:
   - *Premise*: Requirement R4 requires multi-layer visualization: LST, predicted surface temp, SUHII, NDVI, built-up density, land cover, AQ stations, weather stations, groundwater stations, heat-risk zones, population exposure, and proposed interventions, with physical-unit legends and opacity controls.
   - *Observation*: `HeatMap.tsx` only renders single-layer polygon choropleths over light OSM tiles with no station markers, no opacity sliders, and no multi-layer toggles (Observation 4).
   - *Deduction*: The map must be rebuilt into a multi-layer interactive GIS engine using dark CartoDB Matter basemap tiles, layer stacking checkboxes, opacity range sliders, SVG station markers with pulsing status, and dynamic legends with real units (`°C`, `µg/m³`, `mbgl`, `[-1, 1]`, `%`).
3. **Regression Safety & Integration**:
   - *Premise*: The existing test suite contains 91 passing tests verifying hash routing, zone selection, API errors, and sidecar links (Observation 5).
   - *Deduction*: When Agent 7 implements the 10 canonical views and dark theme, the existing route slugs (`prediction`, `compare`, `simulator`, `optimizer`) must remain supported as backward-compatible aliases in `PAGE_MAP`, and the sidecar viewer link in `ZoneDetails` must be preserved to guarantee zero test regressions.

---

## 3. Caveats

1. **Backend Sensor Endpoints**: Backend Agent 6 and Agent 1/2/3/4/5 must provide the live environmental station endpoints (`/api/environmental/stations` or `/api/data/records?kind=monitoring`) for the frontend to display live OpenAQ, Open-Meteo, and CGWB pins. In the absence of live external credentials, graceful no-data fallback states must be presented.
2. **Tile Server Proxy**: The frontend currently relies on `/api/tiles/{z}/{x}/{y}.png`. Direct client-side loading of CartoDB Dark Matter tiles (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) or dark-inverted OSM tiles is recommended to avoid backend rate-limiting or tile caching bottlenecks.
3. **Tailwind CSS v4 Configuration**: Tailwind v4 uses `@tailwindcss/vite` without a `tailwind.config.js`. Theme tokens should be defined via `@theme` directives in CSS or standard CSS custom properties.

---

## 4. Conclusion

1. **Current Status**: The frontend build and tests are healthy and robust (91/91 passing), but the UI styling, application shell, navigation structure, and mapping system require a complete architectural upgrade to satisfy R1 and R4.
2. **Scope of Upgrades for Agent 7**:
   - **Design System**: Full dark-first climate-intelligence design system with obsidian/slate surfaces, monospace telemetry, and Linear-level hairline borders.
   - **Application Shell**: Collapsible sidebar (240px expanded / 64px icon-only / mobile drawer) + Top Command Bar (`Ctrl+K` omni-search, city quick-switch, zone lookup, quick actions).
   - **10 Canonical Views**: Overview Command Center, Live Environmental Map, Heat Analysis, Environmental Analysis (new), Heat Risk & Vulnerability, Explainable AI, Mitigation Planning, Intervention Optimization, AI Climate Assistant, Reports.
   - **Interactive GIS Map**: Reusable multi-layer Leaflet map with dark tiles, point markers for AQ/weather/groundwater stations, multi-layer toggle stack, opacity controls, physical-unit legends, and zone inspection flyout.
   - **Contract Preservation**: Retain backward-compatible route aliases and sidecar link triggers to ensure all 91 tests pass continuously.

---

## 5. Verification Method

To independently verify the findings and any future implementation:

1. **Verify Existing Tests**:
   ```powershell
   npm --prefix frontend test
   ```
   *Expected outcome*: 11 test files pass, 91 tests pass.
2. **Verify Production Build**:
   ```powershell
   npm --prefix frontend run build
   ```
   *Expected outcome*: `tsc -b && vite build` succeeds with zero errors in ~25-30s.
3. **Verify Raster Sidecar Linkage**:
   Inspect `frontend/src/components/zone/ZoneDetails.tsx` and run:
   ```powershell
   npx --prefix frontend vitest run src/tests/mapPageSidecar.test.tsx
   ```
   *Expected outcome*: All 5 tests pass, confirming sidecar link and SUHII °C display.
4. **Verify Routing & Hash Integrity**:
   ```powershell
   npx --prefix frontend vitest run src/tests/integration_challenge.test.ts
   ```
   *Expected outcome*: All 18 challenge tests pass.
