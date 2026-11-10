# Handoff Report: Frontend State & Integration Challenge (Milestone 1)

**Agent:** Challenger M1-2 (Frontend State & Integration Specialist)  
**Parent / Caller ID:** 34ff78fc-de7b-4a98-abfc-54d6c3495098  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_2\`  
**Date:** 2026-11-08  
**Verdict:** **`REQUEST_CHANGES`**  

---

## 1. Observation

1. **Test Suite & Build Results:**
   - Ran `npm test` in `frontend/`:
     ```
     RUN  v3.2.7 D:/Urban-Heat-Resilience-AI/frontend
     ✓ src/tests/zoneCompare.test.ts (6 tests)
     ✓ src/tests/weather.test.ts (3 tests)
     ✓ src/tests/metrics.test.ts (9 tests)
     ✓ src/tests/button.test.tsx (5 tests)
     ✓ src/tests/integration_challenge.test.ts (17 tests)
     ✓ src/tests/api.test.ts (11 tests)

     Test Files  6 passed (6)
          Tests  51 passed (51)
     ```
     Exit code: 0.
   - Ran `npm run build` (`tsc -b && vite build`) in `frontend/`:
     ```
     vite v7.3.7 building client environment for production...
     ✓ 2105 modules transformed.
     dist/assets/index-eINQ-3y0.css     62.63 kB │ gzip:  17.67 kB
     dist/assets/index-BWp46Uah.js     953.28 kB │ gzip: 283.05 kB
     ✓ built in 24.53s
     ```
     Exit code: 0.

2. **`ZoneComparePage.tsx` City Switch State Desynchronization (Lines 31-46):**
   ```typescript
   // Default to the first two zones (or top 2 hotspots)
   const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
   const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);

   const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));
   ```
   `selectedIds` is initialized strictly on component mount. When the user changes the city via `Topbar`, `data` prop updates with new zone features (e.g. `DEL_01`, `DEL_02`), but `selectedIds` retains stale IDs (`["AHM_01", "AHM_02"]`). Consequently:
   - `selectedZones.length` evaluates to 0.
   - `ZoneComparisonChart` receives `zones = []` and returns `null` (disappears from UI).
   - Summary KPIs evaluate to `0.0 °C` and `0` residents.
   - Clicking new city chips adds to the stale array. Once `selectedIds.length` reaches 4 (e.g. `["AHM_01", "AHM_02", "DEL_01", "DEL_02"]`), `toggleZone` rejects any new selections because `selectedIds.length < 4` is false, even though only 2 zones are active.

3. **`App.tsx` Ignores `route.zoneId` (Lines 19, 34-41):**
   ```typescript
   19: const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();
   ...
   34: useEffect(() => {
   35:   if (data.data?.features?.length) {
   36:     const match = data.data.features.find((f: ZoneFeature) => f.properties.id === selectedZone?.id);
   37:     setSelectedZone(match ? match.properties : data.data.features[0].properties);
   38:   }
   39: }, [data.data, city]);
   41: const activeZone = selectedZone || data.data?.features?.[0]?.properties;
   ```
   - `zoneId` is discarded from `useHashRouter()`.
   - On direct deep link (`/#/map?city=Ahmedabad&zone=AHM_03`), `selectedZone` is initialized to `AHM_01`, completely ignoring `zone=AHM_03`.
   - In `ZoneComparePage.tsx` lines 274, 281, clicking "Simulate Interventions" or "Inspect SHAP Drivers" executes `navigate("Intervention simulator", { zone: z.id })`. The hash updates to `/#/simulator?city=Ahmedabad&zone=AHM_03`, but `App.tsx` never binds `route.zoneId` to `selectedZone`, so `SimulatorPage` receives `selectedZone = AHM_01` (wrong zone).

4. **`PAGE_MAP` Missing Plural and Common Route Aliases in `constants.ts` (Lines 54-83):**
   - Slugs registered: `overview`, `map`, `compare`, `prediction`, `explain`, `risk`, `simulator`, `optimizer`, `assistant`, `reports`.
   - Attempting to visit `/#/predictions` (standard plural used in documentation and prompt instructions) yields `PAGE_MAP["predictions"] === undefined`, causing `useHashRouter.ts` (line 11) to fall back to `overview`.

5. **`apiClient.ts` Unhandled Error Types (Lines 13-39):**
   - Line 15: `fetch("/api" + path, ...)` is not enclosed in a try/catch block. Network disconnects reject with `TypeError: Failed to fetch`, which escapes unhandled as a raw `TypeError` instead of `ApiError`.
   - Line 39: `return response.json() as Promise<T>;` is not enclosed in a try/catch block. If an endpoint returns HTTP 200 with HTML (e.g. Vite SPA index fallback on missing API routes), it throws an uncaught `SyntaxError: Unexpected token '<'`.
   - Function signature `request<T>(path: string, body?: unknown)` lacks `AbortSignal` or timeout options.

---

## 2. Logic Chain

1. From Observation 1, the baseline build and Vitest suite pass cleanly, confirming no syntax or static type defects.
2. However, from Observation 2, storing `selectedIds` as initial-only state causes `selectedZones` to collapse to an empty list whenever the user switches cities. This renders the zone comparison table empty, disables the multivariate comparison chart, and traps the user with ghost IDs.
3. From Observation 3, failing to destructure and bind `zoneId` from `useHashRouter` means that deep links with `?zone=...` and inter-page planning triggers in `ZoneComparePage` fail to communicate the active zone to target pages.
4. From Observation 4, omitting plural aliases like `predictions` causes routing to fail silently and drop users on the overview page.
5. From Observation 5, unhandled network rejections and non-JSON responses break consumer error boundaries expecting `ApiError`.
6. Therefore, while Worker M1's structural refactoring was highly effective, these state and routing defects require targeted fixes before approval.

---

## 3. Caveats

- **No Source Code Modified:** Challenger strictly adhered to the constraint "Do not modify source code". Verification tests were executed via `frontend/src/tests/integration_challenge.test.ts` without mutating implementation files.
- **Server-Side Integration:** Tests were performed against client-side state transitions and mocked HTTP responses; backend execution was unchanged.

---

## 4. Conclusion & Required Actions

**Verdict: `REQUEST_CHANGES`**

Worker M1 must apply the following 4 targeted fixes:

1. **Fix `ZoneComparePage.tsx` City State Sync:**
   Add a `useEffect` to reset `selectedIds` when `data` or `city` updates:
   ```typescript
   useEffect(() => {
     if (allZones.length > 0) {
       setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
     }
   }, [city, data]);
   ```
   Or key the component in `App.tsx`: `<ZoneComparePage key={city} ... />`.

2. **Fix `App.tsx` Zone Deep Linking & Navigation Sync:**
   Destructure `zoneId` in `App.tsx` and prioritize `zoneId` when selecting the active zone:
   ```typescript
   const { page, city, zoneId, layer, navigate, setCity, setLayer } = useHashRouter();

   useEffect(() => {
     if (data.data?.features?.length) {
       const match = data.data.features.find((f: ZoneFeature) => f.properties.id === (zoneId || selectedZone?.id));
       setSelectedZone(match ? match.properties : data.data.features[0].properties);
     }
   }, [data.data, city, zoneId]);
   ```

3. **Add Route Aliases in `constants.ts`:**
   Add `predictions: PAGES[3]`, `Predictions: PAGES[3]`, and `simulations: PAGES[6]` to `PAGE_MAP`.

4. **Harden `apiClient.ts` Error Catching:**
   Wrap `fetch` and `response.json()` in try/catch blocks so network rejections and HTML payloads are normalized into `ApiError`.

---

## 5. Verification Method

To independently reproduce and verify these findings:

1. **Run Vitest Integration Suite:**
   ```bash
   cd frontend
   npm test
   ```
   *Expected Output:* 6 test files passed, 51 tests passed, exit code 0 (including the 17 integration challenge tests in `src/tests/integration_challenge.test.ts`).

2. **Verify Production Build:**
   ```bash
   cd frontend
   npm run build
   ```
   *Expected Output:* Production bundle successfully built in `dist/` with zero TypeScript errors.

3. **Inspect Challenge Report:**
   Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_2\challenge.md`.
