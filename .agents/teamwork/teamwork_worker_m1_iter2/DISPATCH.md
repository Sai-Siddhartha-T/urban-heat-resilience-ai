## 2026-11-08T21:38:58Z
You are Worker M1 Iteration 2: Frontend Remediation Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m1_iter2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read the Gate feedback at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md

Read the exact drop-in blueprints provided by the 3 Iteration 2 Explorers:
1. Routing & State synchronization blueprint:
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_1\analysis.md
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_1\handoff.md
2. Shared domain utilities & test integrity blueprint:
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_2\analysis.md
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_2\handoff.md
3. ApiClient error resilience & network error wrapping blueprint:
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\analysis.md
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\handoff.md
   d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_apiClient.ts

Write Ownership:
You exclusively own:
- `frontend/src/App.tsx`
- `frontend/src/lib/utils.ts`
- `frontend/src/lib/constants.ts`
- `frontend/src/pages/ZoneComparePage.tsx`
- `frontend/src/components/charts/ZoneComparisonChart.tsx`
- `frontend/src/components/charts/WeatherTimeSeriesChart.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/src/api.ts`
- `frontend/src/hooks/useHashRouter.ts`
- `frontend/src/tests/*` (`metrics.test.ts`, `weather.test.ts`, `zoneCompare.test.ts`, `api.test.ts`, `button.test.tsx`, `integration_challenge.test.ts`)
DO NOT modify any backend files.

Tasks to Execute:
1. Fix 1: Update `frontend/src/App.tsx`:
   - Destructure `zoneId` from `useHashRouter()`.
   - Update `useEffect` to listen to `[data.data, city, zoneId]`, matching `targetId = zoneId || selectedZone?.id`. Add city-mismatch guard. Key `ZoneComparePage` by `city`. Keep line count well under 150 lines.
2. Fix 2: Shared Domain Utilities & Real Unit Tests:
   - Add the 7 shared domain functions (`calcSuhii`, `classifyRisk`, `calcCoolingPotential`, `validateInterventionCapacity`, `computeWeatherExtremes`, `updateZoneSelection`, `computeZoneDeltas`, `computeSuhiiDisparity`) to `frontend/src/lib/utils.ts` per Explorer 2 blueprint.
   - Refactor `ZoneComparePage.tsx`, `ZoneComparisonChart.tsx`, and `WeatherTimeSeriesChart.tsx` to import and consume these utilities.
   - Update `frontend/src/tests/metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts`: DELETE all local mockup function definitions and import the functions directly from `../lib/utils`.
3. Fix 3: In `ZoneComparePage.tsx`, reset/synchronize `selectedIds` when `city` changes.
4. Fix 4: In `frontend/src/lib/constants.ts`, add plural aliases (`predictions`, `simulations`, `comparisons`, etc.) in `PAGE_MAP`. In `src/tests/integration_challenge.test.ts`, update the Section 3 test assertion to expect `"prediction"` instead of `undefined` for `PAGE_MAP["predictions"]`.
5. Fix 5: In `frontend/src/services/apiClient.ts`, wrap `fetch()` in try/catch to catch network rejections and wrap `response.json()` to catch non-JSON syntax errors, throwing typed `ApiError`. Also support optional AbortSignal. Update `frontend/src/api.ts`.
6. Run Verification:
   - Run `cd frontend; npm run build` (must pass exit code 0).
   - Run `cd frontend; npm test` (all tests in all test files must pass with exit code 0).
7. Deliverables:
   - Document all changes and build/test outputs in `changes.md` and `handoff.md` in your state folder `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m1_iter2\`.
   - Send completion message to orchestrator.
