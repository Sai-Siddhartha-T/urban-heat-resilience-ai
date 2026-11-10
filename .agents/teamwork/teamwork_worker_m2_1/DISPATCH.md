## 2026-11-08T23:07:42Z
You are the Backend Implementation Worker for Milestone 2: Backend Modularization, ML Pipeline & Data Integration Enhancements.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY CONTEXT:
Read ORIGINAL_REQUEST.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md

READ COMPREHENSIVE EXPLORER BLUEPRINTS (Complete Drop-In Implementations):
1. Explorer M2-1 (Modular APIRouters, State decoupling & Fast Startup):
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_1_gen2\analysis.md
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_1_gen2\handoff.md
2. Explorer M2-2 (Spatial Clustering, Optimizer Budget Constraints & AI Guardrails):
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_2_gen2\analysis.md
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_2_gen2\handoff.md
3. Explorer M2-3 (Adapter Unit Test Suite Expansion - 34 passing tests):
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3_gen2\analysis.md
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3_gen2\proposed_test_sources.py
   - d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_3_gen2\handoff.md

WRITE OWNERSHIP (You exclusively own these files):
- `backend/app/main.py`
- `backend/app/routes/` (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`)
- `backend/app/services/state.py`
- `backend/app/services/ml.py`
- `backend/app/services/planning.py`
- `backend/app/services/ai.py`
- `backend/app/services/data.py`
- `backend/app/schemas.py`
- `backend/tests/test_sources.py`
- `backend/tests/conftest.py`

YOUR IMPLEMENTATION TASKS:
1. Modularize `backend/app/main.py`:
   - Create `backend/app/services/state.py` with `state()`, `zone()`, `analyze()`, `STATE`, `LOCK`.
   - Create 8 router modules in `backend/app/routes/` (`heat.py`, `models.py`, `simulation.py`, `optimization.py`, `risk.py`, `data.py`, `ai.py`, `reports.py`).
   - Slim down `backend/app/main.py` (<120 lines) as an assembly root with CORS, static mounts, exception handlers, lifespan, and router includes. Keep backward-compatible re-exports (`state`, `zone`, `overview`).
2. Implement Fast Startup & Disk Model Caching:
   - Fix `backend/app/services/data.py` default baseline `generated_at` timestamp.
   - Fix `backend/app/services/ml.py` `load_or_train()` to reliably reuse cached `.joblib` files.
   - Update `lifespan` in `main.py` with `FAST_STARTUP=1` and `PREWARM_STATE=0` bypass.
   - Update `backend/tests/conftest.py` to enable fast startup and copy pre-trained baseline models into the temporary model dir.
3. Generalized Spatial Clustering in `backend/app/services/ml.py`:
   - Replace rigid `x // 3` with `assign_spatial_partitions()` using 2D KMeans on lat/lon coordinates with quantile fallback, handling 5 to 50+ zones with adaptive sample thresholds (`min_required = 1 if n < 60 else 15`).
   - Preserve 100% backward compatibility with `test_models_spatial_evaluation` (`training: 162, validation: 54, test: 54, buffer: 54`).
4. Financial Budget Model in OR-Tools Optimizer:
   - Add `budget_limit` and `budget_enforced` to `OptimizationRequest` in `backend/app/schemas.py`.
   - Add CapEx/OpEx cost coefficients for all 8 interventions in `backend/app/services/planning.py`.
   - Formulate integer budget constraint in CP-SAT model and return total cost and budget utilization in `OptimizationResponse`.
5. AI Guardrail Regex Refinement in `backend/app/services/ai.py`:
   - Replace brittle `r"\d"` with the 3-step pipeline (whitelist masking, measurement extraction, fact validation).
6. Adapter Test Suite Expansion:
   - Apply the verified 34-test drop-in from `teamwork_explorer_m2_3_gen2/proposed_test_sources.py` to `backend/tests/test_sources.py`.
7. Testing & Verification:
   - Run `pytest backend/tests/test_sources.py -v` (verify 34 passed).
   - Run `pytest backend/tests/test_foundation.py -v` (verify all passed).
   - Run `pytest backend/tests/test_pipeline.py -v` (verify all passed).
   - Run `pytest backend/tests/test_api.py -v` (verify all passed).
   - Run `pytest backend/tests/test_ai.py -v` (verify all passed).
   - Run full backend test suite: `pytest backend/tests/ -v`.
   - Note: on Windows PowerShell, run pytest with `python -m pytest backend/tests/ ...` with `BypassSandbox: true`.
