## 2026-11-10T12:30:04Z

You are specialized AGENT 4: Intervention Simulation and Optimization Engineer working on Milestone M4 (Physical Intervention Simulator & Optimization Engine) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent4_optimization
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_3\handoff.md` first.
Your exclusive file ownership:
- `backend/app/services/planning.py`
- `backend/app/services/optimization.py`
- `backend/tests/test_optimization.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R6):
1. Literature-Grounded Intervention Simulator (`backend/app/services/planning.py`):
   - Ground cooling effects and water consumption for urban greening (trees, vegetation, pocket parks), cool surfaces (cool roofs, cool pavements), and permeable infrastructure in urban climatology literature.
   - Include explicit uncertainty ranges (e.g., lower/upper cooling bounds depending on urban density and humidity).
   - Calculate feasible metrics deltas (LST delta, NDVI delta, albedo delta, runoff reduction).
   - Explicitly label scenario outputs as hypothetical estimates.
2. Physical-Only Combinatorial Optimization Engine (`backend/app/services/optimization.py`):
   - CRITICAL REQUIREMENT: Enforce physical, land-use, and water constraints WITHOUT ANY FINANCIAL BUDGET CONSTRAINTS OR OBJECTIVES.
   - The OR-Tools CP-SAT optimizer must enforce:
     - Physical surface capacities (ground, roof, road area)
     - `land_limit_pct` (max allowable intervention coverage per zone)
     - Protected land prohibition
     - Cool roofs vs roof gardens mutual exclusivity
     - Max vegetation ceiling (`max_vegetation_pct`)
     - Municipal water availability limits (`water_limit` m³/day)
     - 3.0°C cooling saturation curve
     - Objective: Strictly maximize equity-weighted heat risk reduction across vulnerable populations.
     - ZERO financial budget fields, costs, or CapEx/OpEx constraints.
3. Spatial Priority Plans & Water Sensitivity:
   - Generate spatial priority rankings (which zones receive highest priority for intervention) and feasible allocation matrices.
   - Implement 50% water sensitivity contingency analysis (assessing cooling loss if available water drops by half).
4. Solver Execution Stability Guard:
   - Wrap `cp_model.CpSolver().Solve(model)` with safety error trapping and graceful fallback to prevent native C++ access violation crashes on Windows Python 3.14.
5. Verification:
   - Run `pytest backend/tests/test_optimization.py`. Ensure all tests pass.
   - Document all changes and test outputs in `handoff.md`.

Write your report to `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent4_optimization\handoff.md` and send a message when complete.
