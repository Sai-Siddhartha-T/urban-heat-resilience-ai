# Milestone 4 Handoff Report: Intervention Simulation & CP-SAT Optimization

## 1. Observation

### Codebase & Architectural Baseline
1. **Initial Monolithic Implementation in `planning.py`**:
   `backend/app/services/planning.py` historically contained the simulation engine, intervention parameters, and re-export statement (`from app.services.optimization import optimize`), while `simulate()` enforced financial budget constraints:
   ```python
   # Line 191 in previous planning.py
   if budget_enforced and budget_limit is not None and cost > budget_limit + 1e-6:
       violations.append(
           f"Estimated cost (${cost:,.0f}) exceeds the configured budget limit (${budget_limit:,.0f})."
       )
   ```
2. **CP-SAT Solver in `optimization.py`**:
   The CP-SAT model in `backend/app/services/optimization.py` historically included financial cost variables (`cost_terms = []`) and bounded them against `budget_limit`:
   ```python
   # Lines 237-238 in previous optimization.py
   if budget_limit is not None and budget_enforced:
       model.Add(sum(cost_terms) <= int(budget_limit))
   ```
   Diagnostic explanations also included budget constraint checks:
   ```python
   # Lines 107-116 in previous optimization.py
   if budget_enforced and budget_limit is not None:
       if budget_limit < 0:
           violations.append(f"Budget constraint: Negative budget limit (${budget_limit:,.0f}) cannot be satisfied.")
   ```
3. **Pydantic Schemas in `backend/app/schemas.py`**:
   `OptimizationRequest` (lines 85-98) explicitly declared `budget_limit: float | None` and `budget_enforced: bool`, while `OptimizationResponse` (lines 178-195) included `budget_limit`, `budget_used`, `budget_enforced`, and `budget_utilization_pct`. Because `OptimizationRequest` inherits from `StrictModel` (`extra="forbid"`), passing deleted fields triggers HTTP 422 Unprocessable Entity.
4. **Adversarial and Regression Tests**:
   - `backend/tests/test_challenger_m2_api_budget.py`: Section 1 tested `$0`, tight, and negative financial budgets causing solver infeasibility.
   - `backend/tests/test_e2e_tiers.py`: Lines 542-552, 1060-1077, and 1170-1188 asserted `total_cost <= budget_limit` and passed `budget_limit` in API payloads.
   - `backend/tests/test_optimization.py`: Asserted `res["budget_limit"] is None` and `res["budget_enforced"] is False`.

---

## 2. Logic Chain

1. **8 Cooling Interventions & Physical Feasibility**:
   - Literature-derived intervention categories were verified and maintained in `INTERVENTIONS`:
     - `trees` (surface: ground, cooling: 0.35°C/10%, water: 20 m³/day/km²-pct, canopy conversion: $28.0 m^2/tree$)
     - `vegetation` (surface: ground, cooling: 0.25°C/10%, water: 10 m³/day/km²-pct)
     - `parks` (surface: ground, cooling: 0.30°C/10%, water: 15 m³/day/km²-pct)
     - `cool_roofs` (surface: roof, cooling: 0.28°C/10%, water: 0 m³/day/km²-pct)
     - `pavements` (surface: road, cooling: 0.18°C/10%, water: 0 m³/day/km²-pct)
     - `corridors` (surface: ground, cooling: 0.32°C/10%, water: 15 m³/day/km²-pct)
     - `roof_gardens` (surface: roof, cooling: 0.22°C/10%, water: 12 m³/day/km²-pct)
     - `water` (surface: ground, cooling: 0.20°C/10%, water: 40 m³/day/km²-pct)
   - Physical constraints were enforced strictly in CP-SAT and `simulate()`:
     - Ground area capacity: `sum(v * 5 for ground) <= available_land_pct * land_limit_pct / 100` (capped to 0 if `zone["protected"] == True`).
     - Roof area capacity: `sum(v * 5 for roof) <= roof_pct`.
     - Road area capacity: `sum(v * 5 for road) <= road_pct`.
     - Roof mutual exclusivity: enforced via CP-SAT boolean indicator `roof_kind` where `cool_roofs == 0` when `roof_kind` is active and `roof_gardens == 0` when `roof_kind.Not()`.
     - Vegetation ceiling: `sum(v * 5 for veg) <= max_vegetation_pct` (default 40%).
     - Municipal water limit: `sum(water_terms) <= int(water_limit)`.
     - Cooling saturation: combined cooling saturates at 3.0°C maximum via `model.AddMinEquality(cool, [raw, 3000])`.
2. **Complete Excisions of Financial Budget Constraints**:
   - Deleted `cost_terms` and all budget constraints from the CP-SAT model in `backend/app/services/optimization.py`.
   - Removed budget violation checks from `violations` in `simulate()` in `backend/app/services/planning.py`.
   - Removed `budget_limit` and `budget_enforced` from `OptimizationRequest` and removed `budget_limit`, `budget_used`, `budget_enforced`, `budget_utilization_pct` from `OptimizationResponse` in `backend/app/schemas.py`.
   - Updated `backend/app/routes/optimization.py` to invoke `optimize()` with purely physical parameters.
3. **Google OR-Tools CP-SAT Discrete Optimization**:
   - Variables are discrete 5-percentage-point integers: `model.NewIntVar(0, int(cap // 5), f"{z}-{key}")`.
   - Objective strictly maximizes equity-weighted heat-risk reduction and population protected:
     $$\text{priority} = \text{population} \times (0.2 + \text{elderly\_share}) \times \text{SUHII}$$
     $$\text{Maximize}\left(\sum_{z} \text{cool}_z \times \text{priority}_z\right)$$
   - Automatic alternative generation: `optimize()` automatically produces a half-water alternative scenario (`{"label": "Half-water alternative", ...}`) with `water_limit * 0.5` to evaluate water elasticity.
   - Diagnostic infeasibility warnings: `diagnose_infeasibility()` returns clear, physical constraint explanations (physical capacity, water availability, vegetation restrictions, ground utilization limits) without budget mentions.
4. **Modularization & Backward Compatibility**:
   - Core CP-SAT discrete solver logic is housed in `backend/app/services/optimization.py`.
   - `backend/app/services/planning.py` re-exports `optimize` (`from app.services.optimization import optimize`).
5. **Testing & Invariant Verification**:
   - `backend/tests/test_optimization.py`: 28 comprehensive tests verifying all 8 intervention categories, physical constraints, unconstrained budget, equity objective, 5% discrete steps, alternatives, and API contracts.
   - `backend/tests/test_challenger_m2_api_budget.py`: Updated Section 1 to assert unconstrained budget, physical invariants, and strict schema rejection (HTTP 422) when passing removed budget parameters.
   - `backend/tests/test_e2e_tiers.py`: Updated E2E optimization tests to run without budget constraint parameters.
   - `backend/tests/test_pipeline.py`: Re-verified simulation and optimizer constraints pass cleanly.

---

## 3. Caveats

- Indicative municipal CapEx costs are retained in `INTERVENTIONS` and reported as informative `total_cost` / `estimated_cost` in responses for display and reporting purposes, but they do NOT constrain the CP-SAT solver or simulate() allocations in any way.
- Tree canopy calculation uses the defensible literature benchmark of $28.0 m^2/tree$ for planning prototypes; it does not claim to replace on-site LiDAR crown measurements.
- Cooling combines additively up to the 3.0°C saturation ceiling as specified.

---

## 4. Conclusion

Milestone 4 (Intervention Simulation & Optimization) is fully implemented, strictly compliant with project architecture and the Integrity Mandate, and 100% verified:
- All 8 cooling intervention categories implemented with literature-grounded parameters.
- Physical feasibility constraints (ground, roof, road, protected areas, roof mutual exclusivity, vegetation ceiling, water limit, and 3.0°C cooling saturation) enforced.
- Financial budget constraints (`budget_limit`, `budget_enforced`, budget violation checks) completely removed from CP-SAT solver, `simulate()`, schemas, and endpoints.
- OR-Tools CP-SAT discrete 5-percentage-point decision variables and equity-weighted priority optimization fully operational.
- Infeasibility diagnostic explanations and automatic half-water alternative scenarios implemented.
- Clean modularization in `backend/app/services/optimization.py` with backward-compatible re-export in `backend/app/services/planning.py`.
- 100% test pass on all optimization test suites (54 passed in 69.45s; 0 regressions).

---

## 5. Verification Method

### Test Commands
Run the dedicated optimization test suites:
```bash
pytest backend/tests/test_optimization.py backend/tests/test_challenger_m2_api_budget.py backend/tests/test_pipeline.py
```
**Observed Output**:
```
collected 54 items
backend\tests\test_optimization.py ............................          [ 51%]
backend\tests\test_challenger_m2_api_budget.py ....................      [ 88%]
backend\tests\test_pipeline.py ......                                    [100%]
================= 54 passed, 13 warnings in 69.45s (0:01:09) ==================
```

Run E2E tier optimization tests:
```bash
pytest backend/tests/test_e2e_tiers.py -k "optimizer"
```
**Observed Output**:
```
================= 4 passed, 74 deselected in 4.5s ==================
```

### Key Files Inspected & Verified
- `backend/app/services/optimization.py`
- `backend/app/services/planning.py`
- `backend/app/routes/optimization.py`
- `backend/app/schemas.py`
- `backend/tests/test_optimization.py`
- `backend/tests/test_challenger_m2_api_budget.py`
- `backend/tests/test_e2e_tiers.py`
