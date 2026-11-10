# Adversarial Challenge Report: Frontend State & Integration (Milestone 1)

**Challenger:** Challenger M1-2 (Frontend State & Integration Specialist)  
**Date:** 2026-11-08  
**Scope:** URL hash routing, query param persistence, multi-zone compare selection logic, API client error handling, build & test verification.  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_2\`  

---

## Challenge Summary

**Overall risk assessment**: **HIGH**

While the frontend codebase decomposes the 2,164-line monolith into an 86-line orchestrator and passes existing unit tests cleanly with zero TypeScript build errors, adversarial stress testing and empirical execution uncovered **four critical-to-medium integration bugs** across routing, state synchronization, and error handling. Most notably, switching cities breaks the newly introduced `ZoneComparePage` by polluting its local selection state with orphaned zone IDs, and `App.tsx` completely ignores the `zone` URL query parameter, causing deep linking and cross-page planning navigation to silently fail.

---

## Challenges

### [High] Challenge 1: `ZoneComparePage` Stale State on City Switch (Ghost ID Pollution)

- **Assumption challenged**: Worker assumed that initializing `useState<string[]>(defaultSelected)` in `ZoneComparePage.tsx` adequately tracks user zone selections.
- **Attack scenario**:
  1. User navigates to `/#/compare` while target city is `Ahmedabad`. `selectedIds` initializes to `["AHM_01", "AHM_02"]`.
  2. User changes target city to `Delhi` via the `Topbar`.
  3. `ZoneComparePage` re-renders with new Delhi features (`DEL_01`, `DEL_02`, ...).
  4. Because `useState` does not re-initialize on prop changes without an explicit `useEffect` or React `key`, `selectedIds` retains `["AHM_01", "AHM_02"]`.
  5. `allZones.filter(z => selectedIds.includes(z.id))` matches **zero zones**.
  6. The comparison table displays 0 zone columns, summary KPIs collapse to `0.0 °C` and `0 residents`, and `ZoneComparisonChart` returns `null` and completely disappears from the DOM.
  7. When the user attempts to click Delhi zone chips, the 2 stale Ahmedabad IDs count toward the 4-zone ceiling (`selectedIds.length < 4`). Clicking 2 Delhi zones fills the array to length 4 (`["AHM_01", "AHM_02", "DEL_01", "DEL_02"]`), permanently locking out any further selections.
- **Blast radius**: Complete functional breakdown of Feature 4 (Zone Comparison View) whenever a user selects another city while on the Compare page or switches to Compare after changing city.
- **Mitigation**:
  In `ZoneComparePage.tsx`, synchronize `selectedIds` when `data` or `city` changes:
  ```typescript
  useEffect(() => {
    if (allZones.length > 0) {
      setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
    }
  }, [city, data]);
  ```
  Alternatively, key the page component in `App.tsx`: `<ZoneComparePage key={city} ... />`.

---

### [High] Challenge 2: `App.tsx` Omits `zoneId` from `useHashRouter`, Breaking Deep Linking and Cross-Page Navigation

- **Assumption challenged**: Worker assumed that passing `navigate` to components satisfies deep linking and cross-page navigation contracts.
- **Attack scenario**:
  1. User deep-links directly to a specific zone: `/#/map?city=Ahmedabad&zone=AHM_03` or `/#/explain?city=Ahmedabad&zone=AHM_03`.
  2. In `App.tsx`, line 19 only destructures:
     ```typescript
     const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();
     ```
     `zoneId` is discarded.
  3. In `App.tsx` lines 34-39:
     ```typescript
     useEffect(() => {
       if (data.data?.features?.length) {
         const match = data.data.features.find((f: ZoneFeature) => f.properties.id === selectedZone?.id);
         setSelectedZone(match ? match.properties : data.data.features[0].properties);
       }
     }, [data.data, city]);
     ```
     `selectedZone` defaults to `data.data.features[0].properties` (`AHM_01`), completely ignoring `zone=AHM_03` from the URL!
  4. Furthermore, in `ZoneComparePage.tsx`, action buttons execute:
     `navigate("Intervention simulator", { zone: z.id })`
     This updates the URL hash to `/#/simulator?city=Ahmedabad&zone=AHM_03`, but `App.tsx` never binds `route.zoneId` to `selectedZone`. As a result, `SimulatorPage` receives `selectedZone = AHM_01` and simulates the wrong sector!
- **Blast radius**: Broken deep linking across the entire application and silent failure of the "Simulate Interventions" and "Inspect SHAP Drivers" action buttons in `ZoneComparePage`.
- **Mitigation**:
  Destructure `zoneId` from `useHashRouter` in `App.tsx` and sync `selectedZone` whenever `zoneId` changes or data loads:
  ```typescript
  const { page, city, zoneId, layer, navigate, setCity, setLayer } = useHashRouter();

  useEffect(() => {
    if (data.data?.features?.length) {
      const match = data.data.features.find((f: ZoneFeature) => f.properties.id === (zoneId || selectedZone?.id));
      setSelectedZone(match ? match.properties : data.data.features[0].properties);
    }
  }, [data.data, city, zoneId]);
  ```

---

### [Medium] Challenge 3: Hash Router Fails on Plural Slugs (`/#/predictions`)

- **Assumption challenged**: Worker assumed standard exact slug mapping without plural normalization or aliases.
- **Attack scenario**:
  1. A user or markdown link navigates to `/#/predictions` (as specified in the challenge scope and project documentation).
  2. `PAGE_MAP` in `constants.ts` defines `prediction`, `AI prediction`, and `Prediction`, but **not** `predictions`.
  3. In `useHashRouter.ts`:
     ```typescript
     const pageDef = PAGE_MAP[slug] || PAGE_MAP[pathPart] || PAGE_MAP.overview;
     ```
     Because `PAGE_MAP["predictions"]` is `undefined`, the router silently falls back to `overview`.
- **Blast radius**: User confusion and broken links whenever pluralized or alternate page routes are accessed (`/#/predictions`, `/#/simulations`, `/#/reports` vs `/#/report`).
- **Mitigation**:
  Add common route aliases in `frontend/src/lib/constants.ts`:
  ```typescript
  predictions: PAGES[3],
  Predictions: PAGES[3],
  simulations: PAGES[6],
  ```

---

### [Medium] Challenge 4: `apiClient.ts` Throws Raw Uncaught `SyntaxError` and `TypeError`

- **Assumption challenged**: Worker assumed `apiClient.ts` guarantees typed `ApiError` instances for all failure modes.
- **Attack scenario**:
  1. **Scenario A (HTML / Non-JSON 200)**: Under Vite SPA proxy configurations, a misconfigured or 404 upstream endpoint may return HTTP 200 with an HTML index page (`<!DOCTYPE html>`). In `apiClient.ts` line 39:
     ```typescript
     return response.json() as Promise<T>;
     ```
     This is executed outside of any `try/catch`. It throws an unhandled raw `SyntaxError: Unexpected token '<'`, bypassing `ApiError`.
  2. **Scenario B (Network Drops / Offline)**: When the client is offline or the backend server refuses connections, `fetch()` rejects with `TypeError: Failed to fetch`. `request()` has no try/catch around `fetch`, throwing raw `TypeError` instead of a structured `ApiError(0, "Network connection error")`.
  3. **Scenario C (Indefinite Hang)**: `request(path, body)` accepts no `AbortSignal` or timeout. Long-running STAC queries or Earth Engine ingestion calls can lock the request indefinitely.
- **Blast radius**: UI error boundaries that inspect `err instanceof ApiError` fail to identify these exceptions, leaving users with cryptic unhandled promise rejections or infinite spinners.
- **Mitigation**:
  Wrap `fetch` and `response.json()` in `try/catch` blocks inside `apiClient.ts` and return standardized `ApiError` instances:
  ```typescript
  try {
    const response = await fetch(...);
    ...
    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError(response.status, "Invalid JSON response from server");
    }
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err instanceof Error ? err.message : "Network error", err);
  }
  ```

---

## Stress Test Results

| # | Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| 1 | Standard slug routing (`/#/overview`, `/#/map`, `/#/compare`, etc.) | Routes to matching page slug | Routes cleanly to expected slugs | **PASS** |
| 2 | Plural slug routing (`/#/predictions`) | Routes to `prediction` page | Falls back to `overview` (`PAGE_MAP["predictions"]` is `undefined`) | **FAIL (BUG)** |
| 3 | Query param persistence across tab switch (`city=Delhi&zone=DEL_04&layer=ndvi`) | Preserves city, zone, and layer in URL hash | Retains params on navigate (`#/compare?city=Delhi&zone=DEL_04&layer=ndvi`) | **PASS** |
| 4 | Deep linking with `?zone=AHM_03` in `App.tsx` | Sets `selectedZone` to `AHM_03` | Defaults to `AHM_01` (`zoneId` omitted from `App.tsx`) | **FAIL (BUG)** |
| 5 | Cross-page button navigation (`Simulate Interventions` for `AHM_03`) | Switches to Simulator with `selectedZone` = `AHM_03` | URL hash updates, but `selectedZone` in `App.tsx` remains stale | **FAIL (BUG)** |
| 6 | Exceeding 4 zones in `ZoneComparePage` | Caps selection at 4 zones | Blocks 5th zone (`selectedIds.length < 4`) | **PASS** |
| 7 | Deselecting to 0 zones in `ZoneComparePage` | Keeps at least 1 zone selected | Retains last zone (`selectedIds.length > 1`) | **PASS** |
| 8 | City switch while in `ZoneComparePage` | Updates selection to new city's top zones | Retains stale IDs from old city; 0 zones match; chart vanishes; locks slot quota | **FAIL (BUG)** |
| 9 | Empty zone dataset in `ZoneComparePage` | Safe KPI calculation without throwing | Yields `0.0 °C` and `0` residents without error | **PASS** |
| 10 | HTTP 400 Bad Request with JSON detail | Throws `ApiError(400)` with detail message | Throws `ApiError` with status 400 and detail | **PASS** |
| 11 | HTTP 422 Unprocessable Entity (FastAPI validation array) | Throws `ApiError(422)` with stringified array | Throws `ApiError` with JSON string of error array | **PASS** |
| 12 | HTTP 500 with plain text error body | Throws `ApiError(500)` with statusText fallback | Throws `ApiError` with `Internal Server Error` | **PASS** |
| 13 | HTTP 200 with HTML body (Vite SPA fallback / proxy error) | Throws structured `ApiError` | Throws raw uncaught `SyntaxError` | **FAIL (BUG)** |
| 14 | Network disconnect / connection refused | Throws structured `ApiError(0)` | Throws raw uncaught `TypeError: Failed to fetch` | **FAIL (BUG)** |
| 15 | Vitest test suite execution (`npm test`) | All unit and component tests pass | 6 test files, 51 tests passed, 0 failed (exit code 0) | **PASS** |
| 16 | Production bundle build (`npm run build`) | Zero TypeScript errors, clean bundle in `dist/` | 2105 modules transformed, built in 24.53s (exit code 0) | **PASS** |

---

## Unchallenged Areas

- **Leaflet WebGL / Canvas rendering**: DOM canvas rendering was verified via component structure and props rather than an active browser display server.
- **Backend FastAPI integration**: Backend endpoints were verified as unmutated and matching schemas; live network integration was evaluated via synthetic mock contracts.
