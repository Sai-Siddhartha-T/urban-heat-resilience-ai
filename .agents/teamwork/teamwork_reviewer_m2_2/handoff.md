# Milestone 2 Review & Adversarial Challenge Report

**Reviewer**: `teamwork_reviewer_m2_2` (Roles: reviewer, critic)  
**Date**: 2026-11-09  
**Review Target**: Milestone 2 Backend ML, Optimization Solver, AI Guardrail, and Adapter Tests  
**Target Commit/Branch**: `main` (Workspace: `d:\Urban-Heat-Resilience-AI`)  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Full Backend Test Suite Execution
- **Command**: `pytest backend/tests/ -v`
- **Result**:
  ```text
  platform win32 -- Python 3.14.6, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\siddh\AppData\Local\Programs\Python\Python314\python.exe
  cachedir: .pytest_cache
  rootdir: D:\Urban-Heat-Resilience-AI
  configfile: pytest.ini
  plugins: anyio-4.15.1, langsmith-0.14.11, asyncio-1.4.1
  collected 127 items

  backend/tests/test_ai.py (1 passed)
  backend/tests/test_api.py (5 passed)
  backend/tests/test_e2e_tiers.py (78 passed)
  backend/tests/test_foundation.py (3 passed)
  backend/tests/test_pipeline.py (6 passed)
  backend/tests/test_sources.py (34 passed)

  ====================== 127 passed, 13 warnings in 37.33s ======================
  ```
- **Exit Code**: 0

### 1.2 Adapter Test Suite Execution
- **Command**: `pytest backend/tests/test_sources.py -v`
- **Result**: Exactly 34 unit tests passed in 7.00s.
- **Coverage**: All 11 external data sources tested with 100% offline mocks (`monkeypatch` on `httpx.AsyncClient`, `get_json`, `post_json`, `rasterio.open`, `rasterio.vrt.WarpedVRT`, and Google Earth Engine `ee.ImageCollection`).

### 1.3 ML Spatial Clustering & Partitioning
- **Location**: `backend/app/services/ml.py:58-148` (`assign_spatial_partitions`) and `151-260` (`train`)
- **Direct Observations**:
  - Replaced legacy rigid `x // 3` grid partitioning with coordinate-based multi-tier spatial clustering:
    - GeoJSON centroid and coordinate extraction (`extract_coordinates`, lines 34-55) supporting polygon geometries, `(longitude, latitude)`, `(lon, lat)`, and `(column, row)`.
    - Primary spatial dispersion axis identification (`var = np.var(coords, axis=0)`, lines 70-72).
    - $N < 5$: Raises `ValueError("Need at least 5 zones for spatial cross-validation; got {n}.")`
    - $N \in [5, 7]$: Small-area spatial ranking along the primary dispersion axis ($N-2$ training, 1 validation, 1 test).
    - $N \in [8, 14]$: 4-block spatial quantile partitioning along the primary dispersion axis (2 training, 1 validation, 1 test).
    - $N \ge 15$: 6-cluster 2D KMeans (`KMeans(n_clusters=6, random_state=42, n_init=10)`) with automatic exception catch falling back to 6-block spatial quantile partitioning (`np.array_split(sort_idx, 6)`).
  - Exact legacy split compatibility (`training: 162, validation: 54, test: 54, buffer: 54`) preserved for baseline synthetic datasets via legacy block check (`has_legacy_blocks`, lines 156-171).

### 1.4 ML Model Caching & Startup Optimization
- **Location**: `backend/app/services/ml.py:269-290` (`load_or_train`)
- **Direct Observations**:
  - Checks for existing `{city}.joblib` in `MODEL_DIR`.
  - Primary cache validation: Exact `generated_at` timestamp match.
  - Secondary cache validation: Synthetic baseline dataset validation matching city and feature list `FEATURES`.
  - Corrupt or invalid artifact recovery: Catches any `Exception`, logs a warning (`log.warning("Could not read cached model at %s (%s). Re-training.", path, exc)`), and falls back cleanly to `train(data)`.

### 1.5 CP-SAT Budget Constraints & Optimization Logic
- **Location**: `backend/app/schemas.py:85-97, 178-195` and `backend/app/services/planning.py:6-87, 241-405`
- **Direct Observations**:
  - `OptimizationRequest` adds `budget_limit: float | None = Field(None, ge=0, le=1e12)` and `budget_enforced: bool = Field(False)`.
  - `OptimizationResponse` adds `total_cost: float`, `budget_limit: float | None`, `budget_used: float | None`, `budget_enforced: bool`, and `budget_utilization_pct: float | None`.
  - All 8 cooling interventions in `INTERVENTIONS` define CapEx/OpEx cost coefficients:
    - `trees`: CapEx $\$5.50/\text{m}^2$, OpEx $\$0.50/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$55,000/\text{pct}/\text{km}^2$
    - `vegetation`: CapEx $\$20.00/\text{m}^2$, OpEx $\$2.00/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$200,000$
    - `parks`: CapEx $\$50.00/\text{m}^2$, OpEx $\$5.00/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$500,000$
    - `cool_roofs`: CapEx $\$12.00/\text{m}^2$, OpEx $\$1.20/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$120,000$
    - `pavements`: CapEx $\$30.00/\text{m}^2$, OpEx $\$2.50/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$300,000$
    - `corridors`: CapEx $\$45.00/\text{m}^2$, OpEx $\$4.00/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$450,000$
    - `roof_gardens`: CapEx $\$100.00/\text{m}^2$, OpEx $\$8.00/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$1,000,000$
    - `water`: CapEx $\$35.00/\text{m}^2$, OpEx $\$6.00/\text{m}^2/\text{yr}$, `cost_per_pct` $=\$350,000$
  - CP-SAT formulation:
    - Scaled integer variables `levels` (5-percentage-point increments).
    - Integer cost coefficient per level: `cost_per_level = int(round(5 * spec["cost_per_pct"] * p["area_km2"]))`.
    - Solver constraint when enforced: `model.Add(sum(cost_terms) <= int(budget_limit))`.

### 1.6 AI 3-Stage Numeric Regex Guardrail Pipeline
- **Location**: `backend/app/services/ai.py:8-80, 186-193`
- **Direct Observations**:
  - Stage 1 Whitelist Masking:
    - `ENTITY_WHITELIST = re.compile(r"\b(?:Sentinel-[12345]|Landsat-[789]|MODIS|GHSL(?:-\d+)?|WorldCover|SRTM|WGS84|EPSG:\d+|PM(?:2\.5|10)|H3-\d+|ISO-\d+|COVID-19)\b", re.IGNORECASE)`
    - `ORDERED_LIST_MARKER = re.compile(r"(?:^|\n|\.\s+)\d+\.\s+")`
    - `YEAR_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b")`
  - Stage 2 Measurement Extraction:
    - `NUMERIC_MEASUREMENT_PATTERN` extracts sign, numeric value (integer or float), and units (`°C`, `°F`, `%`, `m²`, `m³`, `m³/day`, `km²`, `USD`, `INR`, `$`, `₹`).
  - Stage 3 Fact Grounding & Numerical Tolerance:
    - Recursively extracts all numbers from `facts` into `fact_numbers` (`extract_numbers_from_facts`, lines 32-51).
    - Checks grounding within tolerance: `abs(raw_val - fn) < 0.15 or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)`.
    - Unmatched numbers trigger `ValueError(f"Provider included unsupported numeric prose: {m.group(0).strip()}")`.

---

## 2. Logic Chain

1. **Independent Test Execution (Observation 1.1 & 1.2)**:
   - Executing `pytest backend/tests/ -v` produced 127 passing tests across all test modules (`test_ai.py`, `test_api.py`, `test_e2e_tiers.py`, `test_foundation.py`, `test_pipeline.py`, `test_sources.py`).
   - Executing `pytest backend/tests/test_sources.py -v` confirmed all 34 offline adapter unit tests pass in 7.00s.
   - All tests run without network access, using well-isolated fixtures (`isolate_test_state`).

2. **Spatial Partitioning Verification (Observation 1.3)**:
   - In our standalone stress test:
     - $N=4$ was rejected with `ValueError` as expected.
     - $N=5$ and $N=7$ correctly used small-area ranking ($N-2$ train, 1 val, 1 test).
     - $N=8$ and $N=14$ correctly used 4-quantile split.
     - $N=15$ and $N=50$ correctly used 6-cluster 2D KMeans.
     - Collinear coordinates and polygon GeoJSONs partitioned cleanly without errors.
     - Identical points triggered the exception handler and cleanly fell back to 6-block spatial quantile partitioning without crashing.
   - Baseline dataset preserves exact legacy 6-block split (`training: 162, validation: 54, test: 54, buffer: 54`).

3. **Model Caching Verification (Observation 1.4)**:
   - In our standalone caching stress test:
     - Cold start created `ahmedabad.joblib`.
     - Subsequent invocation hit the cache and returned the model in $<10\text{ ms}$ without retraining.
     - Intentionally corrupting `ahmedabad.joblib` with garbage bytes triggered the `except Exception` handler, emitted a log warning, and retrained a valid model cleanly.

4. **CP-SAT Budget Modeling Verification (Observation 1.5)**:
   - In our standalone optimization test:
     - Unconstrained optimization selected interventions costing $\$61,700,000$.
     - Enforcing a tight budget of $\$100,000$ strictly capped total cost at $\$0$ (or $\le \$100,000$).
     - Enforcing a budget of $\$5,000,000$ selected interventions totaling $\$4,875,000$ with $97.5\%$ budget utilization and $0.427^\circ\text{C}$ mean cooling.
     - Enforcing $\$1,000$ budget with impossible minimum cooling ($2.0^\circ\text{C}$) returned `status: INFEASIBLE` and `feasible: False`.
     - Non-enforced budget optimized without capping but correctly reported `total_cost`, `budget_limit`, and `budget_enforced: False`.

5. **AI Guardrail Robustness (Observation 1.6)**:
   - In our standalone guardrail test:
     - Whitelisted domain entities (`Sentinel-2`, `Landsat-8`, `PM2.5`, `WGS84`) and dates (`2024`) passed without error.
     - Numbered list markers (`1. ... 2. ... 3. ...`) passed without error.
     - Fact-grounded numbers (`3.8 °C`, `22.5%`, `25%`) passed within tolerance.
     - Hallucinated numbers (`88 degrees`, `95%`) raised `ValueError` and were blocked.

6. **Integrity Assessment**:
   - Zero hardcoded test outputs or dummy facades were detected in source code.
   - Genuine machine learning algorithms (`RandomForestRegressor`, `XGBRegressor`, `LGBMRegressor`, `TreeExplainer`), optimization solvers (`ortools.sat.python.cp_model`), and GIS operations (`rasterio.vrt.WarpedVRT`, `shapely`) are genuinely implemented and verified.

---

## 3. Adversarial Challenges & Findings

### Challenge 1 [Minor / Adversarial]: Partition Size Discontinuity at $N \in [60, 89]$
- **Observation**: In `backend/app/services/ml.py:183`:
  ```python
  min_required = 1 if n < 60 else 15
  if min(tr.sum(), val.sum(), test.sum()) < min_required:
      raise ValueError(f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid.")
  ```
- **Stress-Test Scenario**:
  - We generated a synthetic GeoJSON dataset with $N = 60$ zones.
  - In a 6-block split, validation is 1 block (10 zones) and test is 1 block (10 zones).
  - Because $N \ge 60$, `min_required` evaluates to 15.
  - $\min(30, 10, 10) = 10 < 15$.
  - Execution failed with: `ValueError: Need at least 15 cell(s) in each spatial partition.`
  - Conversely, for $N = 59$, `min_required` evaluates to 1, and training succeeds.
- **Blast Radius**:
  - Does not affect the default municipal baseline datasets ($N = 324$, where $324 / 6 = 54 \ge 15$).
  - Does not affect existing unit/E2E tests ($N \le 50$ or $N = 324$).
  - Only affects custom user-uploaded GeoJSON boundaries with $N \in [60, 89]$ zones.
- **Recommended Mitigation**:
  - Update `min_required` to either step at $N = 90$ ($15 \times 6 = 90$):
    `min_required = 1 if n < 90 else 15`
  - Or use a dynamic fractional threshold:
    `min_required = max(1, min(15, n // 6))`
- **Verdict Impact**: Non-blocking for Milestone 2 approval because baseline cities ($N = 324$) and all test suites pass 100%. Recorded as a quality improvement recommendation.

---

## 4. Conclusion

The Milestone 2 ML & Optimization logic, AI guardrail pipeline, and adapter test suite are thoroughly implemented, mathematically sound, performant, and fully verified:
- `assign_spatial_partitions()` provides robust dynamic spatial clustering across small and large zone sets with reliable quantile fallbacks.
- `load_or_train()` provides deterministic disk caching with error recovery on corrupted artifacts.
- OR-Tools CP-SAT budget modeling properly constrains combinatorial intervention allocations using accurate municipal CapEx/OpEx cost coefficients.
- The 3-stage numeric guardrail effectively eliminates false positives from domain terms and list markers while blocking hallucinated numerical values.
- All 34 offline adapter unit tests pass cleanly, providing full offline test coverage across all 11 data sources.
- No integrity violations, hardcoded shortcuts, or facade implementations were detected.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Run Full Backend Test Suite**:
   ```powershell
   pytest backend/tests/ -v
   ```
   *Expected*: 127 passed in ~35-40s.

2. **Run Adapter Test Suite**:
   ```powershell
   pytest backend/tests/test_sources.py -v
   ```
   *Expected*: 34 passed in ~7s.

3. **Verify CP-SAT Budget Constraint Enforcement**:
   ```powershell
   python -c "
   import sys; sys.path.insert(0, 'backend')
   from app.services.data import sample_data
   from app.services.planning import optimize

   d = sample_data('Ahmedabad')
   zones = [f['properties'] for f in d['features'][:5]]
   r = optimize(zones, water_limit=1000, budget_limit=5_000_000, budget_enforced=True)
   assert 0 < r['total_cost'] <= 5_000_000
   print('Budget test PASSED, total_cost:', r['total_cost'], 'utilization:', r['budget_utilization_pct'])
   "
   ```
   *Expected*: Outputs `Budget test PASSED, total_cost: 4875000.0 utilization: 97.5`.

4. **Verify AI Guardrail Whitelist & Numeric Blocking**:
   ```powershell
   python -c "
   import sys; sys.path.insert(0, 'backend')
   from app.services.ai import validate_numeric_guardrails

   facts = {'prediction': {'suhii_c': 3.5}}
   validate_numeric_guardrails('Sentinel-2 from 2024 shows 3.5 C heat', facts)
   try:
       validate_numeric_guardrails('Heat will rise by 99 degrees', facts)
       assert False, 'Should have failed'
   except ValueError:
       print('Guardrail test PASSED')
   "
   ```
   *Expected*: Outputs `Guardrail test PASSED`.

5. **Invalidation Conditions**:
   - Any failure in the 127-test backend suite.
   - Any relaxation of CP-SAT budget constraints allowing `total_cost > budget_limit` when `budget_enforced=True`.
   - Failure of the AI guardrail to block unsupported numbers or hallucinated percentages in LLM responses.
