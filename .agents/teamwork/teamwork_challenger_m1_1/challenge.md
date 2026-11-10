# Empirical Challenge Report: Frontend Robustness & Edge Cases (Milestone 1)

**Challenger:** Challenger M1-1 (Frontend Empirical Stress & Edge Case Challenger)  
**Roles:** Critic, Domain Specialist  
**Working Directory:** `d:\Urban-Heat-Resilience-AI`  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_1\`  
**Target:** Frontend Refactoring by Worker M1 (`frontend/src/*`)  
**Date:** 2026-11-08  
**Verdict:** **`REQUEST_CHANGES`**

---

## 1. Executive Summary

We performed an adversarial empirical investigation into Worker M1's frontend implementation across four primary dimensions:
1. **Static Type Safety & Suppression Audit**: Audited TypeScript compiler strictness, `@ts-*` directives, and `: any` casts.
2. **Production Build Integrity**: Verified `tsc -b && vite build` and inspected bundle output in `frontend/dist/`.
3. **Empirical Edge-Case Testing**: Evaluated empty datasets, null weather fields, single-zone vs. multi-zone behaviors, and hash routing anomalies.
4. **State & Lifecycle Synchronization**: Stress-tested state transitions across city switches and cross-page navigation.

While Worker M1 achieved remarkable code decomposition (reducing `App.tsx` from 2,164 lines to 86 lines) and clean production bundle generation (exit code 0), our adversarial stress-testing identified **two functional edge-case bugs** that degrade the user experience:
- **Bug 1 (High Blast Radius):** `ZoneComparePage.tsx` does not reset `selectedIds` state when the user changes city. This causes `selectedZones` to collapse to an empty array, blanks out the comparison table and charts, and locks the selection counter with ghost IDs from the prior city.
- **Bug 2 (Medium Blast Radius):** `App.tsx` fails to bind `route.zoneId` to `selectedZone`. As a result, deep links (`/#/map?city=Ahmedabad&zone=AHM_05`) and cross-page actions in `ZoneComparePage` ("Simulate Interventions" / "Inspect SHAP Drivers") fail to activate the requested zone.

---

## 2. Empirical Verification Matrix

| # | Challenge Dimension | Test / Command Executed | Expected Outcome | Actual Outcome | Status |
|---|---------------------|-------------------------|------------------|----------------|--------|
| 1 | Strict Type Safety | `npx tsc -b` | Exit code 0, 0 compiler errors | Exit code 0, 0 errors | **PASS** |
| 2 | Hidden Type Casts | Ripgrep `:\s*any\b`, `as any`, `<any>` in `src/` | 0 occurrences | 1 occurrence in `DataDialog.tsx:306` (`d: any`), 1 in `api.ts:5` (`T = any`) | **WARN** |
| 3 | Compiler Suppressions | Ripgrep `@ts-ignore`, `@ts-expect-error`, `@ts-nocheck` | 0 occurrences in `src/` | Exactly 0 occurrences | **PASS** |
| 4 | Vitest Suite | `npx vitest run` | All tests pass, exit code 0 | 6 test files, 51 tests passed, exit code 0 | **PASS** |
| 5 | Production Build | `npm run build` | Valid assets in `dist/`, exit code 0 | 2,105 modules transformed, built in 25.60s | **PASS** |
| 6 | Dist Artifacts | `Get-ChildItem -Recurse frontend/dist` | Valid HTML, CSS, JS bundles | `index.html` (533 B), `index-BWp46Uah.js` (953 kB), `index-eINQ-3y0.css` (62 kB) | **PASS** |
| 7 | Route Fallbacks | Input invalid slug `#/xyz123` | Clean fallback to `overview` | `PAGE_MAP[slug] \|\| PAGE_MAP.overview` falls back cleanly | **PASS** |
| 8 | Route Plural Alias | Input `#/predictions` | Route to Predictions page | Resolves to `overview` because only `prediction` is registered | **FAIL** |
| 9 | City Switch in Compare | Switch city from Ahmedabad to Delhi on `/compare` | Reset selection to Delhi top zones | `selectedIds` retains Ahmedabad IDs; `selectedZones` becomes `[]` | **FAIL** |
| 10 | Zone Deep Link | Load `/#/simulator?city=Ahmedabad&zone=AHM_05` | Active zone is `AHM_05` | `App.tsx` ignores `zoneId`, defaults to `AHM_01` | **FAIL** |
| 11 | Null Weather Inputs | Ingest weather series with `null` temperatures | Filtered out without NaN/crashes | Filtered cleanly via `Number.isFinite` in `WeatherTimeSeriesChart.tsx` | **PASS** |
| 12 | Empty Zone List | Compare page with 0 zones | No crash / division by zero | Handled cleanly; disparity evaluates to `0.0` | **PASS** |

---

## 3. Deep-Dive Challenge Findings

### Challenge Finding 1 (HIGH): `ZoneComparePage.tsx` City Switch State Desynchronization
- **Observation:**
  In `frontend/src/pages/ZoneComparePage.tsx`:
  ```tsx
  31: const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
  32: const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);
  34: const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));
  ```
  `useState` initializes `selectedIds` only when the component mounts. When the user changes `city` via the top bar (e.g. from Ahmedabad to Delhi), `data` prop receives Delhi's zone collection (`DEL_01`, `DEL_02`, ...), but `selectedIds` remains `["AHM_01", "AHM_02"]`.
- **Empirical Failure:**
  1. `selectedZones` evaluates to `[]`.
  2. The Side-by-Side Detailed Metric Comparison table renders zero zone columns.
  3. The `ZoneComparisonChart` bar chart receives `zones = []` and renders nothing.
  4. The summary KPI disparity cards display `+0.0 °C` and `0` residents.
  5. The zone chip selector shows "Active Zones (0/4)". If the user clicks `DEL_01` and `DEL_02`, `selectedIds` becomes `["AHM_01", "AHM_02", "DEL_01", "DEL_02"]` (length 4). Now the user is blocked from selecting a 3rd Delhi zone because `selectedIds.length < 4` is false, and cannot deselect the invisible Ahmedabad zones!
- **Mitigation:**
  In `frontend/src/pages/ZoneComparePage.tsx`, add a `useEffect` listening to `city` or `data` that resets `selectedIds` to `allZones.slice(0, 2).map((z) => z.id)`:
  ```tsx
  useEffect(() => {
    if (allZones.length > 0) {
      setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
    }
  }, [data]);
  ```
  Or pass `key={city}` to `<ZoneComparePage key={city} ... />` in `App.tsx` line 62.

---

### Challenge Finding 2 (MEDIUM): `App.tsx` Ignores URL `zoneId` on Deep Link and Cross-Page Navigation
- **Observation:**
  In `frontend/src/App.tsx`:
  ```tsx
  19: const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();
  ...
  34: useEffect(() => {
  35:   if (data.data?.features?.length) {
  36:     const match = data.data.features.find((f: ZoneFeature) => f.properties.id === selectedZone?.id);
  37:     setSelectedZone(match ? match.properties : data.data.features[0].properties);
  38:   }
  39: }, [data.data, city]);
  ```
  And in `frontend/src/pages/ZoneComparePage.tsx`:
  ```tsx
  274: onClick={() => navigate("Intervention simulator", { zone: zone.id })}
  ```
- **Empirical Failure:**
  1. `useHashRouter()` extracts `zoneId` from query params, but `App.tsx` line 19 does not destructure `zoneId`.
  2. On initial deep-link (`/#/map?city=Ahmedabad&zone=AHM_05`), `selectedZone` is null, so line 37 always falls back to `data.data.features[0].properties` (`AHM_01`).
  3. Clicking "Simulate Interventions" for `AHM_05` updates the URL to `/#/simulator?city=Ahmedabad&zone=AHM_05`, but `App.tsx` does not synchronize `selectedZone` with the URL, so `SimulatorPage` continues simulating `AHM_01`.
- **Mitigation:**
  Destructure `zoneId` from `useHashRouter()` in `App.tsx`:
  ```tsx
  const { page, city, layer, zoneId, navigate, setCity, setLayer } = useHashRouter();
  ```
  And in `useEffect`:
  ```tsx
  useEffect(() => {
    if (data.data?.features?.length) {
      const targetId = zoneId || selectedZone?.id;
      const match = data.data.features.find((f: ZoneFeature) => f.properties.id === targetId);
      setSelectedZone(match ? match.properties : data.data.features[0].properties);
    }
  }, [data.data, city, zoneId]);
  ```

---

### Challenge Finding 3 (LOW): Plural Route Aliases Missing in `PAGE_MAP`
- **Observation:**
  In `frontend/src/lib/constants.ts`:
  `PAGES` contains slug `"prediction"`.
  When a user enters `/#/predictions` or follows external documentation referencing `#predictions`, `PAGE_MAP["predictions"]` is `undefined`, so `useHashRouter.ts` falls back to `overview`.
- **Mitigation:**
  Add plural aliases to `PAGE_MAP` in `frontend/src/lib/constants.ts`:
  ```ts
  PAGE_MAP["predictions"] = PAGE_MAP["prediction"];
  PAGE_MAP["reports"] = PAGE_MAP["reports"];
  PAGE_MAP["compare"] = PAGE_MAP["compare"];
  ```

---

### Challenge Finding 4 (LOW): Residual `: any` in `DataDialog.tsx:306`
- **Observation:**
  In `frontend/src/components/modals/DataDialog.tsx:306`:
  ```tsx
  {status.data?.catalog?.map((d: any, idx: number) => (
  ```
- **Empirical Failure:**
  `frontend/src/types/data.ts` already defines `DatasetCatalogItem` with exact types (`name`, `type`, `description`, `live_configured`, `env_keys`). Using `: any` is unnecessary and violates the strict typing requirement.
- **Mitigation:**
  Import `DatasetCatalogItem` and replace `(d: any, idx: number)` with `(d: DatasetCatalogItem, idx: number)`.

---

## 4. Verification Evidence & Commands

All observations were independently executed and confirmed:
1. `npx tsc -b` -> 0 errors.
2. `npx vitest run` -> 6 test files, 51 tests passed.
3. `npm run build` -> 2,105 modules compiled, output in `frontend/dist/`.
4. Reproduction test suite `frontend/src/tests/integration_challenge.test.ts` successfully reproduced Finding 1, Finding 2, Finding 3, and Finding 4.

---

## 5. Final Verdict

**`REQUEST_CHANGES`**

The codebase structure, modularity, type system, and build health are exceptionally solid. Addressing the two state/routing synchronization bugs (Finding 1 and Finding 2) along with the minor alias and typing cleanups (Finding 3 and Finding 4) will make the frontend fully robust and ready for production deployment.
