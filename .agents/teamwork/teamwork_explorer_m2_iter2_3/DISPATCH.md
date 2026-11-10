# Dispatch: Milestone 2 Iteration 2 Spatial Partitioning & Challenger Tests Specialist (explorer_m2_iter2_3)

## Context
Working Directory: d:\Urban-Heat-Resilience-AI
State Directory: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3
Original Request Path: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Gate Status Document: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Reviewer M2-2 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_reviewer_m2_2\handoff.md
Challenger M2-1 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md
Challenger M2-2 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\handoff.md

## Objective
Investigate and design the exact drop-in remediation for spatial partitioning threshold and challenger test suite integration:
1. **Dynamic Partition Cell Threshold in `backend/app/services/ml.py`**:
   - Reviewer M2-2 identified that in `ml.py:183`, `min_required = 1 if n < 60 else 15` creates an artificial failure for custom GeoJSON uploads with $N \in [60, 89]$ zones because validation has $N // 6 < 15$ cells.
   - Design the fix: `min_required = max(1, min(15, n // 6))` so that custom boundaries with $N \in [60, 89]$ zones partition without error.
2. **Challenger Test Suite Integration**:
   - Challenger M2-1 created `backend/tests/test_challenger_m2_api_budget.py` (20 tests).
   - Challenger M2-2 created `backend/tests/test_challenger_m2.py` (27 tests).
   - Review both files to ensure they can run cleanly and reliably as permanent parts of the pytest suite, bringing total backend test count to 174 tests.

## Deliverable
Write your complete remediation blueprint to `handoff.md` in your state folder with exact drop-in code. Remember: Explorer recommends fix strategy and provides exact code blueprints, but does NOT modify source files directly.


## 2026-11-09T08:20:32Z
You are the Spatial Partitioning & Challenger Tests Specialist for Milestone 2 Iteration 2 of the Urban Heat Resilience & Mitigation Platform.

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md

Your workspace: d:\Urban-Heat-Resilience-AI
Your dedicated state folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3
Read your full dispatch instructions at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3\DISPATCH.md
Read the Gate Status at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Read Reviewer M2-2's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_reviewer_m2_2\handoff.md
Read Challenger M2-1's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md
Read Challenger M2-2's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\handoff.md

Investigate `backend/app/services/ml.py` and the newly authored challenger test suites:
1. In `backend/app/services/ml.py:183`:
   - Fix the partition cell threshold discontinuity where `min_required = 1 if n < 60 else 15` fails for custom GeoJSONs with $N \in [60, 89]$ zones.
   - Design the exact fix: `min_required = max(1, min(15, n // 6))` so all custom zone counts partition cleanly.
2. Review the new empirical test suites created by the Challengers:
   - `backend/tests/test_challenger_m2_api_budget.py` (20 tests)
   - `backend/tests/test_challenger_m2.py` (27 tests)
   - Ensure they integrate seamlessly into the permanent pytest test suite so that `pytest backend/tests/` executes all 174 tests with 100% pass rate.

Provide the exact drop-in code blueprint in `handoff.md`.
Send a message back to the orchestrator upon completion. Remember: Explorers investigate and recommend blueprints, but do NOT modify source code files.
