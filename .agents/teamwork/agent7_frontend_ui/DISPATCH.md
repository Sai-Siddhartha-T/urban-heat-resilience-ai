## 2026-11-10T12:28:41Z
You are specialized AGENT 7: Frontend, Integration, Testing and Documentation Engineer working on Milestone M6 (World-Class Frontend Redesign & Geospatial Map Platform) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent7_frontend_ui
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_1\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_1\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_1\handoff.md` first.
Your exclusive file ownership:
- `frontend/src/` (all styles, components, pages, hooks, services, types)
- `frontend/src/tests/`
- `README.md`
- `docs/`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R1 & R4):
1. Design System Redesign (Dark-First Climate Intelligence):
   - Transform `styles.css` and Tailwind styling from light green into a dark-first climate-intelligence design system with obsidian/slate surfaces (`#080c11`, `#0e141d`, card surfaces `#121924`), hairline borders (`rgba(255,255,255,0.08)`), crisp accents (amber `#f59e0b`, emerald `#10b981`, cyan `#06b6d4`, rose `#f43f5e`), monospace numeric telemetry font (JetBrains Mono / Fira Code / monospace), and Linear-level interface precision.
2. Collapsible Shell & Command Palette:
   - Rebuild `Sidebar.tsx`: Collapsible navigation supporting 240px expanded state, 64px icon-only rail, and mobile drawer overlay with smooth transitions.
   - Rebuild `Topbar.tsx`: Add a top command bar (`CommandBar.tsx`) supporting `Ctrl+K` / `⌘K` command palette for omni-search, city quick-switching (Ahmedabad, Delhi, Hyderabad), zone lookup, and quick navigation.
3. 10 Canonical Views:
   - Implement the 10 distinct views required by R1:
     1. Overview Command Center (`OverviewPage.tsx`)
     2. Live Environmental Map (`MapPage.tsx`)
     3. Heat Analysis (`HeatPage.tsx` or `PredictionsPage.tsx` + zone comparisons)
     4. Environmental Analysis (`EnvironmentalPage.tsx` - new dedicated view showcasing Open-Meteo hourly/daily weather charts, OpenAQ air quality stations, and CGWB groundwater trends)
     5. Heat Risk & Vulnerability (`RiskPage.tsx`)
     6. Explainable AI (`ExplainPage.tsx`)
     7. Mitigation Planning (`SimulatorPage.tsx`)
     8. Intervention Optimization (`OptimizerPage.tsx` - physical constraints only, zero budget fields)
     9. AI Climate Assistant (`AssistantPage.tsx`)
     10. Reports (`ReportsPage.tsx`)
   - In `constants.ts` and `useHashRouter.ts`: Ensure backward-compatible aliases exist (`compare`, `prediction`, `simulator`, `optimizer`, `predictions`, `simulations`) so all existing test routes continue to resolve cleanly.
4. Geospatial Platform & Interactive Multi-Layer Map (R4):
   - In `HeatMap.tsx` and map components:
     - Use dark tiles (e.g. CartoDB Dark Matter `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png` or styled Leaflet layer).
     - Multi-layer toggle stack: Land Surface Temperature (LST), predicted surface temp, SUHII, NDVI, building density, land cover, air-quality stations (OpenAQ/CPCB), weather stations (Open-Meteo), groundwater stations (CGWB), heat-risk zones, population exposure, and proposed interventions.
     - Add opacity controls, layer visibility checkboxes, and dynamic physical-unit legends (`°C`, `µg/m³`, `mbgl`, `[-1, 1]`, `m³/day`, `%`).
     - Zone inspection flyout/modal.
     - CRITICAL: In `ZoneDetails.tsx`, preserve the `sidecar://biomolecular_structure_viewer` link for raster layers (`data-testid="zone-sidecar-link"`) so `src/tests/mapPageSidecar.test.tsx` passes!
5. Verification:
   - Run `npm --prefix frontend test` (all 91 tests must pass).
   - Run `npm --prefix frontend run build` (build must succeed with zero TypeScript or Vite errors).
   - Document all changes and test outputs in `handoff.md`.
