# Dispatch: Milestone 2 Iteration 2 Remediation Worker (worker_m2_iter2)

## Context
Working Directory: d:\Urban-Heat-Resilience-AI
State Directory: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m2_iter2
Original Request Path: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Gate Status Document: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Explorer 1 Blueprint: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\handoff.md
Proposed AI Module: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\proposed_ai.py
Explorer 3 Blueprint: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3\handoff.md
Challenger M2-1 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md
Challenger M2-2 Report: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_2\handoff.md

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objective
Implement all 5 remediation items identified during Gate Iteration 1 using the verified drop-in blueprints:

1. **AI Guardrail Regex & Fact Grounding (`backend/app/services/ai.py`)**:
   - Apply the verified implementation from Explorer 1 (`proposed_ai.py`):
     - In `ENTITY_WHITELIST`: add spatial resolution expressions `|(?:10|15|20|30|60|100|250|500|1000)[-\s]?m\b|\b[125][-\s]?km\b`.
     - In `NUMERIC_MEASUREMENT_PATTERN`: use atomic capture `(?=(?P<value>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?))(?P=value)` to eliminate catastrophic backtracking into digits, include metric units (`m`, `km`, `cm`, `mm`, `ha`), and harden lookbehind to `(?<![\w#])`.
     - In `extract_numbers_from_facts()`: only add `int(round(val))` when `abs(val) >= 1.0` (eliminates zero-rounding leakage for small fractions $< 1.0$).
     - In `validate_numeric_guardrails()`: guard absolute tolerance with `(abs(raw_val - fn) < 0.15 if fn != 0 else abs(raw_val) < 1e-6)`.

2. **Test Rate Limiter Bypass (`backend/app/main.py` & `backend/tests/conftest.py`)**:
   - In `backend/app/main.py:60-65`: check `if os.getenv("FAST_STARTUP") == "1" or os.getenv("TESTING") == "1": pass` before enforcing the 180 req/min limit.
   - In `backend/tests/conftest.py`: set `os.environ["TESTING"] = "1"`, and add an autouse fixture `reset_rate_limit` that clears `app.main.RATE` before and after each test.

3. **Spatial Partition Dynamic Cell Threshold (`backend/app/services/ml.py`)**:
   - In `assign_spatial_partitions()` line 116: require `min_cluster_req = max(1, min(15, n // 6))` so any imbalanced KMeans cluster triggers the safe 6-block quantile fallback.
   - In `train()` line 183: set `min_required = max(1, min(15, n // 6))` so custom GeoJSON boundaries with $N \in [60, 89]$ zones partition cleanly.

4. **Permanent Regression Tests in `backend/tests/test_challenger_m2.py`**:
   - Add `test_zone_counts_60_to_89_partition_cleanly` to verify $N \in [60, 89]$ zones.
   - Update lines 334-368 from defect demonstrations to permanent regression assertions (verifying `10m` is accepted, scientific notation `1.85e-3` is parsed as a single number, and hallucinated `0.1°C` is rejected).

5. **Verification**:
   - Run the complete monolithic test suite:
     `pytest backend/tests/ -v`
   - Verify that all 174+ tests pass cleanly with exit code 0.

## Deliverable
Write your complete handoff report to `handoff.md` in your state folder following the 5-component handoff protocol:
- Executive Summary
- Exact File Modifications
- Full Test Suite Execution Output (174+ passing tests)
- Verification Method


## 2026-11-09T08:39:51Z
You are the Backend Implementation Worker for Milestone 2 Iteration 2 of the Urban Heat Resilience & Mitigation Platform.

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md

Your workspace: d:\Urban-Heat-Resilience-AI
Your dedicated state folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m2_iter2
Read your full dispatch instructions at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_worker_m2_iter2\DISPATCH.md
Read the Gate Status at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
Read Explorer 1's blueprint at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\handoff.md
Read Explorer 1's proposed AI module at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\proposed_ai.py
Read Explorer 3's blueprint at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3\handoff.md
Read Challenger M2-1's report at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m2_1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement the 5 verified remediation items:
1. `backend/app/services/ai.py`:
   - Replace with or apply the verified code from Explorer 1's `proposed_ai.py`:
     - In `ENTITY_WHITELIST`: add spatial resolution expressions `|(?:10|15|20|30|60|100|250|500|1000)[-\s]?m\b|\b[125][-\s]?km\b`.
     - In `NUMERIC_MEASUREMENT_PATTERN`: use atomic capture `(?=(?P<value>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?))(?P=value)`, include metric units (`m`, `km`, `cm`, `mm`, `ha`), and harden lookbehind to `(?<![\w#])`.
     - In `extract_numbers_from_facts()`: only add `int(round(val))` when `abs(val) >= 1.0` (eliminates zero-rounding leakage).
     - In `validate_numeric_guardrails()`: guard absolute tolerance with `(abs(raw_val - fn) < 0.15 if fn != 0 else abs(raw_val) < 1e-6)`.
2. `backend/app/main.py`:
   - In rate limiting middleware (lines 60-65): bypass rate limiting when running under tests:
     `if os.getenv("FAST_STARTUP") == "1" or os.getenv("TESTING") == "1": pass`
3. `backend/tests/conftest.py`:
   - Set `os.environ["TESTING"] = "1"` at top.
   - Add autouse fixture `reset_rate_limit` that clears `app.main.RATE` before and after each test.
4. `backend/app/services/ml.py`:
   - In `assign_spatial_partitions()` line 116: require `min_cluster_req = max(1, min(15, n // 6))` before accepting KMeans clusters, else raise ValueError to trigger quantile fallback.
   - In `train()` line 183: set `min_required = max(1, min(15, n // 6))`.
5. `backend/tests/test_challenger_m2.py`:
   - Add `test_zone_counts_60_to_89_partition_cleanly` to verify $N \in [60, 89]$ zones.
   - Update lines 334-368 from defect demonstrations to permanent regression tests (asserting `10m` is accepted, `1.85e-3` is parsed as single float, and hallucinated `0.1°C` is rejected).
6. Run the complete test suite:
   pytest backend/tests/ -v
   and verify that ALL 174+ tests pass cleanly (100% pass rate).

Document your changes and test output in `handoff.md` in your state folder. Send a message to the orchestrator upon completion.
