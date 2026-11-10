## 2026-11-08T21:28:28Z
You are Explorer M1-Iter2-2: Shared Domain Utilities & Test Integrity Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_2

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read the Gate failure details in:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_reviewer_m1_2\handoff.md
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_reviewer_m1_2\review.md

Your tasks for Milestone 1 Iteration 2:
1. Address the test integrity violation identified by Reviewer M1-2:
   - In `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts`, functions were declared locally inside the test files.
   - Design shared production utility functions in `frontend/src/lib/utils.ts` (or `frontend/src/lib/calculations.ts`):
     - `calcCoolingPotential(zone: ZoneProperties): number`
     - `calcSuhii(properties: ZoneProperties): number`
     - `classifyRisk(score: number): RiskLevel`
     - `validateInterventionCapacity(...)`
     - `computeWeatherExtremes(...)`
     - `updateZoneSelection(currentIds: string[], targetId: string, maxSelection?: number): string[]`
     - `computeZoneDeltas(...)`
2. Update `ZoneComparePage.tsx` and `ZoneComparisonChart.tsx` to import and consume these shared utility functions, eliminating formula duplication.
3. Update `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts` to import these functions directly from `../lib/utils`, ensuring the test suite genuinely tests production application code.
4. Provide precise drop-in code recommendations for the Worker.
5. Write your report to `analysis.md` and complete `handoff.md` in your state folder.
6. Send completion message to orchestrator. Do not modify source code.
