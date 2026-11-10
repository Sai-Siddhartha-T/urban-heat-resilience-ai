## 2026-11-09T13:54:07Z
You are AGENT 4: Intervention Simulation and Optimization Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_optimization_m4\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Your exclusive write ownership:
- `backend/app/services/optimization.py` (create)
- `backend/app/services/planning.py` (enhance, re-export optimization)
- `backend/app/routes/optimization.py`
- `backend/app/schemas.py` (OptimizationRequest and OptimizationResponse definitions)
- `backend/tests/test_optimization.py` or updates to optimization tests

Tasks:
1. 8 Cooling Intervention Categories:
   Implement and verify all 8 cooling interventions:
   (1) Tree planting (`trees`, canopy conversion $28.0 m^2/tree$), (2) Vegetation expansion (`vegetation`), (3) Urban parks & green spaces (`parks`), (4) Cool roofs (`cool_roofs`), (5) Reflective pavements (`pavements`), (6) Green corridors (`corridors`), (7) Rooftop gardens (`roof_gardens`), (8) Water-based cooling (`water`).
2. Physical Simulation & Feasibility Constraints:
   - Ground surface area capacity: `available_land_pct`.
   - Roof surface area capacity: `roof_pct`.
   - Road surface area capacity: `road_pct`.
   - Strict land protection: ground interventions prohibited if `zone["protected"] == True`.
   - Roof mutual exclusivity: cool roofs and rooftop gardens cannot coexist in the same zone.
   - Vegetation ceiling: total added vegetative coverage <= `max_vegetation_pct` (default 40%).
   - Municipal water limit: water consumption <= `water_limit` (m³/day).
   - Cooling saturation: combined cooling saturates at 3.0°C maximum.
   - Do NOT convert SHAP values directly into cooling estimates. Use defensible literature-derived parameters.
3. CRITICAL CHANGE — REMOVE FINANCIAL BUDGET CONSTRAINTS:
   - Completely delete `budget_limit` and `budget_enforced` from the CP-SAT solver constraints!
   - Delete financial budget optimization and budget-dependent restriction logic.
   - Update `OptimizationRequest` and `OptimizationResponse` schemas in `backend/app/schemas.py` and `routes/optimization.py` to remove budget constraint parameters.
   - In `simulate()`, remove budget violation checks from `violations`.
   - Retain physical, environmental, surface, water, and cooling constraints.
4. Google OR-Tools CP-SAT Discrete Optimization:
   - Maximize equity-weighted heat-risk reduction and population protected:
     $\text{priority} = \text{population} \times (0.2 + \text{elderly\_share}) \times \text{SUHII}$.
   - Discrete 5-percentage-point decision variables.
   - Infeasibility explanations: return exact physical violation reasons.
   - Alternative scenarios: automatically produce a half-water alternative scenario to evaluate water elasticity.
5. Modularization:
   - Extract CP-SAT optimization logic to `backend/app/services/optimization.py`.
   - In `backend/app/services/planning.py`, import and re-export `optimize` for backward compatibility.
6. Validation & Testing:
   - Update any tests that assert budget constraint failures (e.g. in `test_challenger_m2_api_budget.py` or `test_pipeline.py`) so they test the unconstrained budget / physical constraints.
   - Add comprehensive tests in `backend/tests/test_optimization.py`.
   - Run `pytest` and ensure all tests pass with 0 regressions.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_optimization_m4\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method with exact test execution results.
When done, message the orchestrator.
