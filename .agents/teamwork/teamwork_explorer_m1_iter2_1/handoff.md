# Handoff Report: Routing & State Synchronization Architecture

**Agent:** Explorer M1-Iter2-1 (Routing & State Synchronization Specialist)  
**Parent / Caller ID:** 34ff78fc-de7b-4a98-abfc-54d6c3495098  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_1\`  
**Date:** 2026-11-08  
**Task Type:** Hard Handoff (Investigation & Architecture Design Complete)

---

## 1. Observation

1. **`frontend/src/App.tsx:19, 34-41` Discards `zoneId` and Fails to Synchronize:**
   - Line 19: `const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();` ignores the returned `zoneId`.
   - Line 34-39: `useEffect(() => { ... }, [data.data, city]);` does not list `zoneId` in its dependency array.
   - Line 36: `const match = data.data.features.find((f: ZoneFeature) => f.properties.id === selectedZone?.id);` matches strictly against `selectedZone?.id`. When deep-linking via `/#/simulator?zone=AHM_03` or navigating from `ZoneComparePage`, `selectedZone` is either `null` or a previous zone, defaulting selection to `data.data.features[0].properties` (`AHM_01`).
   - Line 41: `const activeZone = selectedZone || data.data?.features?.[0]?.properties;` provides no validation that `selectedZone` belongs to the currently active city, risking mismatched cross-city state during asynchronous transitions.

2. **`frontend/src/pages/ZoneComparePage.tsx:24-46, 274, 281` Suffers from City Switch Stale State & Disconnected Navigation:**
   - Lines 24-27: `export function ZoneComparePage({ data, navigate }: ZoneComparePageProps)` omits destructuring `city`, `selected`, `onSelect`, and `notify` from props.
   - Lines 31-34: `selectedIds` is stored in React state `useState<string[]>(defaultSelected)` with no `useEffect` or keying to reset when `city` changes.
   - When switching from Ahmedabad (`AHM_01`, `AHM_02`) to Delhi (`DEL_01`, `DEL_02`), `selectedIds` retains `AHM_01`, `AHM_02`. Consequently, `selectedZones = allZones.filter((z) => selectedIds.includes(z.id))` evaluates to `[]`. The table becomes empty, the comparison chart unmounts, and the user is locked out after adding 2 Delhi chips because `selectedIds.length < 4` is violated.
   - Lines 274, 281: Action buttons call `onClick={() => navigate("Intervention simulator", { zone: z.id })}` without invoking `onSelect?.(z)`.

3. **`frontend/src/lib/constants.ts:54-83` Lacks Plural and Title Route Slugs in `PAGE_MAP`:**
   - `PAGE_MAP` maps `prediction` and `simulator`, but lacks `predictions`, `simulations`, `comparisons`, `risks`, `maps`, and `reports` (singular).
   - Visiting `/#/predictions` fails the map lookup and defaults to `PAGE_MAP.overview`, dropping the user on the Overview page.

4. **`frontend/src/tests/integration_challenge.test.ts:79-85` Asserts the Pre-Fix Failure:**
   - Line 79-85: Contains `expect(PAGE_MAP["predictions"]).toBeUndefined()`. If Worker M1-Iter2 adds `predictions` to `PAGE_MAP` without updating this test, `npm test` will fail.

5. **`frontend/src/hooks/useHashRouter.ts:75-80` Does Not Clear `zoneId` on City Change:**
   - Line 77: `setCity` executes `navigate({ city })`, preserving `route.zoneId` in the query string across cities (`#/simulator?city=Delhi&zone=AHM_03`).

---

## 2. Logic Chain

1. From Observation 1, because `zoneId` is discarded from `useHashRouter()` and omitted from `useEffect` dependencies, route-based zone parameters cannot influence application state.
2. Destructuring `zoneId` in `App.tsx` and matching `targetId = zoneId || selectedZone?.id` in `useEffect` with dependency array `[data.data, city, zoneId]` guarantees that any navigation with `{ zone: id }` or URL deep-link immediately selects the requested zone.
3. From Observation 2, React preserves `useState` across re-renders when a component remains mounted. When `city` updates, `selectedIds` retains IDs from the old city. Adding a synchronization `useEffect` inside `ZoneComparePage.tsx` and adding `key={city}` to `<ZoneComparePage key={city} ... />` in `App.tsx` guarantees that stale ghost IDs are purged immediately upon city switch.
4. From Observation 2, calling `onSelect?.(z)` in `ZoneComparePage` planning buttons updates React state directly in addition to triggering URL hash navigation, eliminating race conditions.
5. From Observation 3, populating `PAGE_MAP` with plural and title-case aliases (`predictions`, `Predictions`, `simulations`, `Simulations`, etc.) ensures reliable route resolution for all user and documentation links.
6. From Observation 4, aligning `integration_challenge.test.ts` to assert that plural routes resolve to their target pages ensures the test suite passes cleanly.
7. From Observation 5, passing `navigate({ city, zoneId: "" })` in `setCity` guarantees clean URLs without residual zone parameters from previous cities.

---

## 3. Caveats

- **Read-Only Constraint:** As an Explorer, no project source code was modified. Complete drop-in code implementations are documented in `analysis.md` and this handoff.
- **Related Milestone 1 Iteration 2 Scope:** Domain calculation refactoring (`src/lib/utils.ts`) and `apiClient.ts` error hardening are companion tasks for Worker M1-Iter2 assigned across the milestone gate remediations. Drop-in code provided here is designed to be fully compatible with those refactorings.

---

## 4. Conclusion

The routing and state synchronization issues in Milestone 1 are completely isolated and understood. Worker M1-Iter2 should apply the drop-in replacements documented in Section 3 of `analysis.md`:
1. **`App.tsx`:** Destructure `zoneId`, update `useEffect` with `[data.data, city, zoneId]`, add `handleSelectZone` with URL sync, guard `activeZone` against city mismatches, and key `ZoneComparePage` by `key={city}`. Line count is 95 lines (<150 constraint).
2. **`ZoneComparePage.tsx`:** Destructure all props (`city`, `selected`, `onSelect`, `navigate`, `notify`), add `useEffect` to reset/sanitize `selectedIds` when `city` or `data` changes, and invoke `onSelect?.(z)` on planning action buttons.
3. **`constants.ts`:** Register plural and title-case route aliases in `PAGE_MAP`.
4. **`useHashRouter.ts`:** Update `setCity` to call `navigate({ city, zoneId: "" })`.
5. **`integration_challenge.test.ts`:** Update line 79 to assert that `#predictions` and `#/simulations` resolve to `prediction` and `simulator`.

---

## 5. Verification Method

1. **Verify Source Replacement Files:**
   Check `frontend/src/App.tsx`, `frontend/src/pages/ZoneComparePage.tsx`, and `frontend/src/lib/constants.ts` against the blueprints in `analysis.md`.
2. **Execute Full Test Suite:**
   ```bash
   cd frontend
   npm test -- --run
   ```
   Must pass all tests (including `integration_challenge.test.ts` and `zoneCompare.test.ts`) with exit code 0.
3. **Execute Production Build:**
   ```bash
   cd frontend
   npm run build
   ```
   Must complete `tsc -b && vite build` with 0 errors and produce production bundles in `dist/`.
4. **Verify App.tsx Constraint:**
   ```bash
   (Get-Content frontend/src/App.tsx).Length
   ```
   Must output < 150 lines.
