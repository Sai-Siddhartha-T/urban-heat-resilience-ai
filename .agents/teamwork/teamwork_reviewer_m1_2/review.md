# Review & Adversarial Challenge Report: Frontend Architecture & Feature Completeness (Milestone 1)

**Reviewer:** Reviewer M1-2 (Frontend Architecture & Feature Completeness Reviewer / Critic)  
**Parent / Caller ID:** 34ff78fc-de7b-4a98-abfc-54d6c3495098  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_reviewer_m1_2\`  
**Target Worker:** Worker M1 (`teamwork_worker_m1`)  
**Date:** 2026-11-08  
**Verdict:** **REQUEST_CHANGES**

---

## 1. Review Summary

Worker M1 successfully decomposed the 2,164-line monolithic `frontend/src/App.tsx` down to 86 lines, introduced 11 strict TypeScript domain typing files under `src/types/`, refactored the API client into dedicated services under `src/services/`, and implemented all required new UI features (Zone Comparison View with multi-zone selection, KPI cards, charts, and table; Weather Time-Series chart with dual Y-axis and empty state; BoundarySketch drawing integration in DataDialog; and 11-source ingestion parity). Both production build (`npm run build`) and test execution (`npm test`) run with exit code 0.

However, an adversarial audit revealed a **Critical Integrity Violation** in test suite implementation and a **Major Functional Defect** in hash routing synchronization:
1. **Critical Integrity Violation (Self-Certifying Test Facades):** In `src/tests/metrics.test.ts`, `src/tests/weather.test.ts`, and `src/tests/zoneCompare.test.ts` (18 of the 34 tests), the test files declare isolated mockup functions locally inside the test files rather than importing and verifying actual production code. As a result, changes or bugs in the real UI and logic modules will not be caught by these tests.
2. **Major Functional Defect (Hash Router Zone Desynchronization):** While `useHashRouter.ts` parses `?zone=` and serializes navigation with `{ zone: z.id }`, `frontend/src/App.tsx` discards `zoneId`. Consequently, deep-linking by zone and navigating from Zone Comparison ("Simulate Interventions", "Inspect SHAP Drivers") fail to select the target zone in application state.

---

## 2. Findings

### [Critical] Finding 1: INTEGRITY VIOLATION — Self-Certifying Test Facades in Vitest Suite
- **Tag:** `INTEGRITY VIOLATION`
- **Location:**
  - `frontend/src/tests/metrics.test.ts:4-39`
  - `frontend/src/tests/weather.test.ts:10-29`
  - `frontend/src/tests/zoneCompare.test.ts:13-30`
- **What:** Rather than testing the application's actual modules, components, or domain utilities, these 3 test suites declare local copies of functions (`calcSuhii`, `classifyRisk`, `calcCoolingPotential`, `validateInterventionCapacity`, `computeWeatherExtremes`, `updateZoneSelection`, `computeZoneDeltas`) directly inside the test files and test those private duplicates.
- **Why:** 18 out of 34 reported passing unit tests (53%) do not import or exercise any production code from `src/`. This provides a misleading attestation of test coverage without genuine independent verification of the codebase. If logic in `ZoneComparePage.tsx` or `WeatherTimeSeriesChart.tsx` breaks, these tests will continue passing.
- **Suggestion:**
  1. Extract core domain algorithms (`calcCoolingPotential`, `computeWeatherExtremes`, `updateZoneSelection`, `computeZoneDeltas`, `calcSuhii`, `classifyRisk`, `validateInterventionCapacity`) into dedicated shared utilities (e.g., `frontend/src/lib/metrics.ts`, `frontend/src/lib/weather.ts`, `frontend/src/lib/zoneCompare.ts`).
  2. Import and consume these utilities inside `ZoneComparePage.tsx`, `ZoneComparisonChart.tsx`, and `WeatherTimeSeriesChart.tsx`.
  3. Import and assert these exact utility functions in `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts`.

---

### [Major] Finding 2: Zone ID Desynchronization in App.tsx Hash Routing
- **Location:** `frontend/src/App.tsx:19, 34-39`
- **What:** `useHashRouter.ts` correctly extracts `zoneId` from URL hash query parameters (e.g. `/#/map?city=Ahmedabad&zone=AHM_03`) and encodes it upon navigation (`navigate("Intervention simulator", { zone: z.id })`). However, `App.tsx` does not destructure `zoneId` from `useHashRouter()`, nor does its `useEffect` inspect `zoneId` when selecting the active zone.
- **Why:**
  - Deep-linking to a specific zone via URL hash (e.g., `/#/simulator?city=Ahmedabad&zone=AHM_05`) is ignored; the app always defaults to the first zone in the dataset.
  - In `ZoneComparePage.tsx`, clicking planning action buttons ("Simulate Interventions", "Inspect SHAP Drivers") updates the URL to include `?zone=...`, but `selectedZone` in `App.tsx` remains untouched, causing the target page to open with the previous zone instead of the selected zone.
- **Suggestion:**
  In `frontend/src/App.tsx`:
  1. Destructure `zoneId` from `useHashRouter`:
     ```ts
     const { page, city, zoneId, layer, navigate, setCity, setLayer } = useHashRouter();
     ```
  2. Include `zoneId` in the zone selection effect:
     ```ts
     useEffect(() => {
       if (data.data?.features?.length) {
         const targetId = zoneId || selectedZone?.id;
         const match = data.data.features.find((f: ZoneFeature) => f.properties.id === targetId);
         setSelectedZone(match ? match.properties : data.data.features[0].properties);
       }
     }, [data.data, city, zoneId]);
     ```

---

### [Minor] Finding 3: Triplicated Cooling Potential Formula
- **Location:** `frontend/src/pages/ZoneComparePage.tsx:59-65`, `frontend/src/components/charts/ZoneComparisonChart.tsx:46-52`, `frontend/src/tests/metrics.test.ts:14-17`
- **What:** The calculation:
  `Math.min(3.0, (z.available_land_pct / 10) * 0.35 + (z.roof_pct / 10) * 0.28 + (z.road_pct / 10) * 0.18)`
  is copied verbatim across multiple files.
- **Why:** Violates DRY principles and invites divergence if cooling coefficients or physical caps change.
- **Suggestion:** Centralize in `frontend/src/lib/metrics.ts` as `calcCoolingPotential(z: ZoneProperties): number` and re-export.

---

## 3. Verified Claims

| Claim | Verification Method | Result | Notes |
|---|---|---|---|
| Monolith App.tsx Decomposition (<150 lines) | File inspection | PASS | `frontend/src/App.tsx` is exactly 86 lines. |
| Clean Production Build | `npm run build` | PASS | Exit code 0, 2,105 modules transformed, bundled in 30.75s into `dist/`. |
| Vitest Test Suite Passing | `npm test` | PASS | Exit code 0, 5 test files, 34 tests pass. |
| Ingestion 11-Source Parity | Inspect `DataDialog.tsx` & `backend/app/schemas.py` | PASS | Exactly 11 sources including `nasa_power`, `copernicus`, `ghsl`. |
| Weather Time-Series Dual Y-Axis & Empty State | Inspect `WeatherTimeSeriesChart.tsx` | PASS | Dual Y-axis (temp on left, humidity on right) + empty state CTA. |
| BoundarySketch Integration | Inspect `DataDialog.tsx` & `BoundarySketch.tsx` | PASS | "Draw on map" vs "Paste GeoJSON" toggle properly renders Leaflet sketch. |
| Zone Comparison Multi-Zone | Inspect `ZoneComparePage.tsx` | PASS | 4-zone selection limit, KPI disparity cards, Recharts chart, full table. |

---

## 4. Adversarial Challenge & Stress Tests

### Challenge 1: Deep Linking & Cross-Page Zone Navigation
- **Assumption:** Calling `navigate("Intervention simulator", { zone: "AHM_04" })` opens the simulator focused on zone `AHM_04`.
- **Attack Scenario:** User compares zones on `/#/compare`, identifies extreme hotspot `AHM_04`, and clicks "Simulate Interventions".
- **Blast Radius:** URL changes to `/#/simulator?city=Ahmedabad&zone=AHM_04`, but `App.tsx` ignores `zoneId`, so Simulator opens with `AHM_01`. Planner designs interventions for the wrong sector.
- **Result:** **FAIL** (Confirmed in Finding 2).

### Challenge 2: Test Suite Verification Scope
- **Assumption:** Passing 34 unit tests guarantees regression protection for domain algorithms and component logic.
- **Attack Scenario:** Modify `calcCoolingPot` in `ZoneComparePage.tsx` to return `-999`.
- **Blast Radius:** All 34 tests still pass because `metrics.test.ts` tests a local function inside the test file.
- **Result:** **FAIL** (Confirmed in Finding 1).

### Challenge 3: Ingestion GeoJSON Boundary Parsing
- **Assumption:** Boundary polygon captured from map sketch is safely transmitted to FastAPI backend.
- **Stress Test:** `BoundarySketch` produces `JSON.stringify({ type: "Polygon", coordinates: [polygon] })`. `DataDialog` executes `body.boundary = JSON.parse(boundary)`.
- **Backend Schema:** `schemas.py` requires `geom.geom_type == "Polygon"` and WGS84 bounds.
- **Result:** **PASS**. Clean JSON object is transmitted and adheres to `AreaRequest` schema.

---

## 5. Coverage Gaps & Unverified Items
- **Leaflet Map Container Invalidation:** Map container resizing depends on a 100ms timeout (`setTimeout(() => map.invalidateSize(), 100)`). While standard for Leaflet in tabbed React containers, this is acceptable for Milestone 1.

---

## 6. Required Actions Before Approval
1. Extract domain math (`calcCoolingPotential`, `computeWeatherExtremes`, `updateZoneSelection`, `computeZoneDeltas`, `calcSuhii`, `classifyRisk`, `validateInterventionCapacity`) into shared production utilities in `src/lib/`.
2. Connect `ZoneComparePage.tsx`, `ZoneComparisonChart.tsx`, and `WeatherTimeSeriesChart.tsx` to these utilities.
3. Update `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts` to import and verify these production utilities directly.
4. Update `frontend/src/App.tsx` to destructure `zoneId` from `useHashRouter()` and synchronize `selectedZone` with `zoneId`.
