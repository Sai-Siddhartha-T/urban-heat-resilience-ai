# Milestone 2 Backend API, Thread-Safety & Budget Optimizer Challenge Report

**Agent**: `teamwork_challenger_m2_1`  
**Role**: Backend API & Budget Challenger (critic, specialist)  
**Date**: 2026-11-09  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Scope & Test Suite Execution
- **Empirical Test Suite**: Created and executed `backend/tests/test_challenger_m2_api_budget.py` containing 20 adversarial test cases.
- **Execution Command**:
  ```bash
  python -m pytest backend/tests/test_challenger_m2_api_budget.py -v
  ```
- **Execution Result**:
  ```
  platform win32 -- Python 3.14.6, pytest-9.2.0, pluggy-1.7.0
  20 passed, 13 warnings in 22.39s
  ```

---

### 1.2 CP-SAT Budget Optimizer Observations (`backend/app/services/planning.py`, `backend/app/schemas.py`)

1. **$0 Budget with Zero Cooling ($min\_cooling = 0.0$)**:
   - `planning.optimize(zones, water_limit=1000, min_cooling=0.0, budget_limit=0, budget_enforced=True)` returned:
     - `feasible: True`, `status: "OPTIMAL"`, `total_cost: 0.0`, `budget_used: 0.0`, `water_used: 0.0`, `mean_cooling: 0.0`.
     - `budget_utilization_pct: None` (avoids ZeroDivisionError via `planning.py:374`).
     - All zone coverage selections were empty `{}`.
2. **$0 Budget with Positive Cooling ($min\_cooling = 0.5$)**:
   - `planning.optimize(zones, water_limit=1000, min_cooling=0.5, budget_limit=0, budget_enforced=True)` returned:
     - `feasible: False`, `status: "INFEASIBLE"`, `total_cost: 0.0`, `budget_used: 0.0`.
     - `violations`: `["Requested minimum mean cooling is incompatible with land, roof, road, protection, vegetation, water, or budget constraints."]`.
     - Failed gracefully without uncaught solver exceptions.
3. **Infinite Budget ($1,000,000,000)**:
   - `planning.optimize(zones, water_limit=5000, min_cooling=0.0, budget_limit=1_000_000_000, budget_enforced=True)` returned:
     - `feasible: True`, `mean_cooling: 0.287`, `total_cost: 1,320,000.0`.
     - Invariant `budget_used <= 1_000_000_000` strictly held (`1,320,000 <= 1,000,000,000`).
4. **Very Tight Budget ($10,000)**:
   - Minimum 5% tree intervention for a 1 km² zone costs $5 \times 55,000 \times 1.0 = \$275,000$.
   - For $min\_cooling = 0.0$, solver returned `feasible: True`, `total_cost: 0.0 <= 10,000`.
   - For $min\_cooling = 0.3$, solver returned `feasible: False`, `status: "INFEASIBLE"`.
5. **Strict Budget Invariant ($budget\_used \le budget\_limit$)**:
   - For $budget\_limit = 1,500,000$, solver returned `total_cost: 1,485,000.0` and `budget_utilization_pct: 99.0%`.
   - Invariant `budget_used <= budget_limit` strictly held.
6. **Schema Validation & Rejection of Negative / Invalid Budget**:
   - `POST /api/optimization/run` with `{"budget_limit": -500, "budget_enforced": True}` returned `HTTP 422 Unprocessable Entity` (`Input should be greater than or equal to 0`).
   - `POST /api/optimization/run` with `{"budget_limit": "a_lot", "budget_enforced": True}` returned `HTTP 422 Unprocessable Entity`.
   - Direct call `planning.optimize(..., budget_limit=-1000, budget_enforced=True)` returned `feasible: False`, `status: "INFEASIBLE"` cleanly.
7. **Unenforced Budget Flag ($budget\_enforced = False$)**:
   - `POST /api/optimization/run` with `budget_limit = 5000, budget_enforced = False` allowed solver to allocate interventions totaling $>\$5000$ and reported `budget_enforced = False` and `total_cost`.

---

### 1.3 State Store Concurrency & Thread-Safety Observations (`backend/app/services/state.py`)

1. **Cold-Start Concurrent Loading**:
   - Cleared `STATE` cache via `clear_state("Ahmedabad")`.
   - Fired 20 concurrent threads calling `state("Ahmedabad")` simultaneously.
   - All 20 threads returned identical valid dictionary instances without race conditions, corruption, or duplicate database queries. `with LOCK:` in `state.py:30` serialized initial load safely.
2. **Multi-City Concurrent Reads**:
   - Fired 30 concurrent threads calling `state()`, `get_city_overview()`, and `zone()` across `"Ahmedabad"`, `"Delhi"`, and `"Hyderabad"`.
   - 0 errors, 100% success rate, 324 zones verified per city.
3. **Concurrent Retraining Race**:
   - Background thread triggered `analyze(..., retrain=True)` while 10 reader threads made 100 rapid calls to `get_city_overview("Ahmedabad")`.
   - 0 reader exceptions. Atomic reference swap of `STATE[req.city]` under `with LOCK:` prevents reader exposure to half-initialized structures.
4. **FastAPI Client Asynchronous Concurrency Burst**:
   - Fired 30 concurrent requests across 6 endpoints (`/api/overview`, `/api/heat/map`, `/api/models`, `/api/xai/importance`, `/api/heat/predict`, `/api/reports/generate`) using `ThreadPoolExecutor(max_workers=8)`.
   - 100% (30/30) returned `HTTP 200 OK`.

---

### 1.4 APIRouter Edge Cases Observations Across All 8 Routers

1. **Router 1: Heat (`heat.py`)**:
   - Invalid city query parameter (`/api/overview?city=Atlantis`) -> `HTTP 422`.
   - Non-existent zone in predict (`/api/heat/predict`, `zone_id="NON_EXISTENT"`) -> `HTTP 404` (`"Zone not found in this city."`).
   - Extra forbidden payload fields -> `HTTP 422` (`extra="forbid"` on `StrictModel`).
   - `/api/cities` -> `HTTP 200` with 3 municipal centers.
2. **Router 2: Models (`models.py`)**:
   - Invalid city in `/api/models`, `/api/models/train`, `/api/xai/importance` -> `HTTP 422`.
   - Non-existent zone in `/api/xai/explain` -> `HTTP 404`.
   - Omitted `zone_id` in `/api/xai/explain` -> Defaults gracefully to highest-risk zone (`HTTP 200`).
3. **Router 3: Simulation (`simulation.py`)**:
   - Unknown intervention key (`{"space_mirror": 50}`) -> `HTTP 422`.
   - Coverage $> 100\%$ or negative -> `HTTP 422`.
   - Negative tree count or tree count $> 500,000$ -> `HTTP 422`.
   - Negative water limit -> `HTTP 422`.
   - Non-existent `zone_id` -> `HTTP 404`.
4. **Router 4: Optimization (`optimization.py`)**:
   - Duplicate `zone_ids` (`["z1", "z1"]`) -> `HTTP 422` (`"Duplicate zones are not allowed."`).
   - Non-existent `zone_id` -> `HTTP 404`.
   - List length $> 30$ zones -> `HTTP 422`.
   - Infeasible constraints (zero water + 2.5°C cooling) -> `HTTP 200` with `feasible: False`, solver status `"INFEASIBLE"`, and detailed violation message.
5. **Router 5: Risk (`risk.py`)**:
   - Weights $< 0.1$ or $> 3.0$ -> `HTTP 422`.
   - Non-existent `zone_id` -> `HTTP 404`.
   - Custom weights -> `HTTP 200` with recalculated risk distribution.
6. **Router 6: Data (`data.py`)**:
   - Invalid record kind -> `HTTP 422`.
   - Missing longitude when latitude is provided -> `HTTP 422`.
   - Inverted date range (`end_date < start_date`) or range $> 366$ days -> `HTTP 422`.
   - Non-polygon GeoJSON or area $> 4$ square degrees -> `HTTP 422`.
7. **Router 7: AI (`ai.py`)**:
   - Empty message or message $> 2000$ characters -> `HTTP 422`.
   - Unknown provider (`"skynet"`) -> `HTTP 422`.
   - Non-existent `zone_id` -> `HTTP 404`.
   - Valid chat with local provider -> `HTTP 200` with `fallback: True` and structured evidence summary.
8. **Router 8: Reports (`reports.py`)**:
   - Non-existent report identifier -> `HTTP 404` (`"Report not found."`).
   - Invalid city in report generation -> `HTTP 422`.
   - Generation lifecycle -> `HTTP 200` returning `id`, followed by `HTTP 200` on JSON, CSV (with expected field headers), and Markdown (with synthetic demonstration disclaimer).

---

### 1.5 System-Level Defects Discovered During Stress Testing

#### Defect 1: In-Memory Rate Limiter Test Starvation
- **File**: `backend/app/main.py:60-65`
- **Verbatim Code**:
  ```python
  key = request.client.host if request.client else "local"
  now = time.monotonic()
  q = RATE[key]
  while q and now - q[0] > 60:
      q.popleft()
  if len(q) > 180:
      return JSONResponse({"detail": "Rate limit reached. Retry in one minute."}, 429)
  q.append(now)
  ```
- **Observed Behavior**:
  - Full test suite execution (`python -m pytest backend/tests/`) generates over 210 requests in ~35 seconds.
  - At request #181, the rate limiter trips, returning `HTTP 429 Too Many Requests` to all subsequent test cases.
  - Causes 31 cascading test failures in `test_e2e_tiers.py` and `test_foundation.py`.
  - When executed independently, `test_e2e_tiers.py` passes 78/78 tests in 33.14s.
- **Root Cause**: `main.py` lacks a test-environment bypass (e.g., checking `os.getenv("FAST_STARTUP") == "1"` or `os.getenv("TESTING") == "1"`), and `backend/tests/conftest.py` does not clear `app.main.RATE` between tests.

#### Defect 2: AI Guardrail Regex Backtracking and Zero-Tolerance Hallucination Bypass
- **Files**: `backend/app/services/ai.py:16-29, 42, 71-75`
- **Observed Behavior**:
  1. *Regex Backtracking on Metric Units*: Sentence `"Sentinel-2 captured 10m resolution imagery."` fails validation with `ValueError: Provider included unsupported numeric prose: 1` because `m` is missing from the unit regex (`m[²23]` only), causing `\d+` to backtrack and extract `"1"` from `"10m"`.
  2. *Fact Zero-Rounding Bypass*: `extract_numbers_from_facts()` inserts `0` into `fact_numbers` via `int(round(val))` whenever any property is $< 0.5$. Because absolute tolerance is `abs(raw_val - fn) < 0.15`, any fabricated number in `(-0.15, 0.15)` (such as `0.0001`, `0.05`, `0.10`) is treated as matching `0`, allowing small hallucinated statistics to bypass the guardrail undetected.

---

## 2. Logic Chain

1. **APIRouter & State Verification**:
   - All 8 APIRouters were directly probed with valid and adversarial payloads.
   - Pydantic models with `extra="forbid"` and parameter validators reliably rejected invalid inputs with `HTTP 422`.
   - Non-existent resources reliably raised `HTTP 404`.
   - Concurrent stress tests with 20-30 threads demonstrated that `threading.RLock()` in `backend/app/services/state.py` prevents race conditions and data corruption.
2. **CP-SAT Budget Optimizer Verification**:
   - The CP-SAT solver formulations in `backend/app/services/planning.py` strictly enforce the constraint $\sum \text{cost\_terms} \le \text{budget\_limit}$ when `budget_enforced=True`.
   - The invariant `budget_used <= budget_limit` strictly held across $0, tight ($10k), and large ($1B) budgets.
   - $0 budget evaluated without division-by-zero errors.
3. **Defect Impact Assessment**:
   - Defect 1 (Rate limiter test starvation) prevents the entire test suite from passing together as a monolithic run, breaking CI/CD guarantees.
   - Defect 2 (AI guardrail regex backtracking and zero-tolerance bypass) breaks the contractual requirement that AI assistant prose accepts valid satellite resolution numbers while strictly blocking ungrounded statistics.
4. **Conclusion**:
   - While the APIRouter modularization, state concurrency, and budget optimizer logic are sound and verified, Defect 1 and Defect 2 must be addressed by Worker M2 to achieve a clean milestone release.

---

## 3. Caveats

- Real external network APIs (Open-Meteo, NASA POWER, Sentinel STAC) were tested offline using mocks and local fixtures in accordance with test isolation requirements.
- Streaming SSE responses were not tested as the AI assistant endpoint operates over unary JSON requests (`/api/ai/chat`).
- Concurrency was evaluated using up to 30 simultaneous OS worker threads; distributed cluster concurrency across multiple OS processes was not tested.

---

## 4. Conclusion & Final Verdict

**VERDICT: REQUEST_CHANGES**

The APIRouters, thread-safe state store, and CP-SAT budget optimizer are **EMPIRICALLY APPROVED**. However, full Milestone 2 sign-off requires remediation of the two identified system-level defects:

### Required Action Items for Worker M2:

1. **Test Environment Rate Limiter Bypass**:
   - In `backend/app/main.py:53`, bypass the rate limiter when running under tests:
     ```python
     if os.getenv("FAST_STARTUP") == "1" or os.getenv("TESTING") == "1":
         # Bypass in-memory rate limiting during automated test suites
         pass
     else:
         # Rate limit logic
     ```
   - Alternatively, add an autouse fixture in `backend/tests/conftest.py` that clears `app.main.RATE` after each test function.
2. **Remediate AI Guardrail Regex and Zero-Rounding Leakage**:
   - In `backend/app/services/ai.py`:
     - Update `NUMERIC_MEASUREMENT_PATTERN` to prevent backtracking into digits before letters, and support metric units (`m`, `km`) and scientific notation (`[eE][-+]?\d+`).
     - In `extract_numbers_from_facts()`, do not add `int(round(val))` when `abs(val) < 1.0` and `val != 0`, preventing hallucinated statistics in `(-0.15, 0.15)` from matching 0.

---

## 5. Verification Method

To independently verify the empirical stress tests and reproduce the findings:

1. **Run Challenger Stress-Test Suite**:
   ```bash
   python -m pytest backend/tests/test_challenger_m2_api_budget.py -v
   ```
   *Expected*: All 20 tests pass in ~22 seconds.

2. **Run Full Test Suite to Observe Rate Limiter Trip**:
   ```bash
   python -m pytest backend/tests/
   ```
   *Expected*: Passes first ~140 tests, then trips rate limiter at request #181, generating 31 `HTTP 429` failures in `test_e2e_tiers.py` and `test_foundation.py`.

3. **Verify Isolated E2E Tiers Pass Rate Without Rate Limiter Trip**:
   ```bash
   python -m pytest backend/tests/test_e2e_tiers.py
   ```
   *Expected*: 78 passed in ~33 seconds.

4. **Reproduce Regex Backtracking False Positive**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'backend'); from app.services.ai import validate_numeric_guardrails; validate_numeric_guardrails('Captured 10m imagery.', {'prediction': {'suhii_c': 25.0}})"
   ```
   *Expected*: `ValueError: Provider included unsupported numeric prose: 1`
