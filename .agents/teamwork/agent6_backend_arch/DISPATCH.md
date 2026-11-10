## 2026-11-10T12:28:22Z

You are specialized AGENT 6: Backend Architecture, API and Database Engineer working on Milestone M0 (Backend Stabilization & Core Architecture) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent6_backend_arch
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_2\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md` and `PROJECT.md` first.
Your exclusive file ownership:
- `backend/app/main.py`
- `backend/app/routes/`
- `backend/app/services/state.py`
- `backend/app/schemas/` and `backend/app/schemas.py`
- `backend/app/db.py`
- `backend/app/migrations.py`
- Backend integration tests

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Fix Mode Resolution in `backend/app/services/state.py`:
   Update `resolve_mode(mode: str | None = None) -> str`:
   When `mode` is explicitly passed (`"demo"` or `"normal"`), return it.
   When `mode is None`, check `os.getenv("HEATWISE_DEMO_MODE")` or `os.getenv("HEATWISE_MODE")` or `os.getenv("TESTING")`. If set to `"1"`, `"true"`, or `"demo"`, return `"demo"`; otherwise return `"normal"`.
   This unblocks 97 test failures where legacy test fixtures expect demo data without explicitly passing `mode="demo"` on every query param.
2. Schema & Endpoint Parity for Groundwater:
   In `backend/app/schemas.py`, add `"groundwater"` to `AreaRequest.source` enum/literal.
   In `backend/app/routes/data.py:ingest`, wire the groundwater ingestion handler so calls to `source="groundwater"` succeed.
   Ensure clean import compatibility between `schemas.py` and `schemas/evidence.py`.
3. OR-Tools Solver Windows Stability Guard:
   In `backend/app/services/optimization.py`, wrap the call to `cp_model.CpSolver().Solve(model)` with a protected execution guard. Catch any runtime exceptions or platform-specific errors and gracefully degrade to a feasible heuristic allocation or clean failure without causing native Windows Python 3.14 crashes.
4. Structured Logging & Graceful Exceptions:
   In `backend/app/main.py`, configure structured logging with timestamps, levels, and request paths.
   Update exception handlers so that missing external credentials (like `OPENAQ_API_KEY` or Earth Engine) return informative responses with `status="unavailable"` and setup instructions rather than unhandled 422 / 500 errors.
5. Verification:
   Run `pytest backend/tests/test_backend_m6_architecture.py backend/tests/test_analytical_mode.py backend/tests/test_evidence_api.py`.
   Run `pytest backend/tests/test_sources.py backend/tests/test_satellite.py`.
   Document all test output and changes in `handoff.md`.

Write your report to `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent6_backend_arch\handoff.md` and send a message when complete.
