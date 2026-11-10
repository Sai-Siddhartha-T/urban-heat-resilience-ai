# Milestone 2 ML Spatial & AI Guardrail Empirical Challenge Report

**Agent**: `teamwork_challenger_m2_2`  
**Role**: Empirical Challenger (critic, specialist)  
**Date**: 2026-11-09  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Spatial Partitioning Observations
- **Test File**: `backend/tests/test_challenger_m2.py::TestSpatialClusteringStress` (12 tests) and `TestModelTrainingWithCustomPartitions` (1 test).
- **Tool Command**: `python -m pytest backend/tests/test_challenger_m2.py -k "Spatial or Training" -v`
- **Output**: 13 passed in 12.8s.
- **Specific Scenarios Tested**:
  1. Under-threshold zone count ($N=3, N=4$): `backend/app/services/ml.py:64-67` correctly raises `ValueError: Need at least 5 zones for spatial cross-validation; got 3.`
  2. Minimal 5-zone city: `assign_spatial_partitions()` allocates 3 training, 1 validation, 1 test, 0 buffer.
  3. Quantile split ($N=8, N=12$): Allocates 4-block quantile split (50% train, 25% val, 25% test).
  4. Large city ($N=25, N=50$): Allocates 6-block partitions without empty folds.
  5. Collinear configurations: Zones collinear along longitude (identical lon, varying lat) or along latitude (identical lat, varying lon) automatically evaluate axis variance `var = np.var(coords, axis=0)` (`ml.py:71-72`) and select the non-zero dispersion axis.
  6. Pathological geometries: Concentric rings and zero-area geometries (Points, LineStrings, collapsed polygons) are handled safely via Shapely centroid extraction in `extract_coordinates()` (`ml.py:34-55`).
  7. End-to-end `train()` integration: Successfully fits Random Forest, XGBoost, and LightGBM models on custom dynamic folds, and computes finite confidence intervals.

---

### 1.2 AI Guardrail Observations

#### Bug A: Catastrophic Regex Backtracking on Satellite Resolutions and Unrecognized Units (`10m`, `30m`)
- **Code Reference**: `backend/app/services/ai.py:16-29`
  ```python
  NUMERIC_MEASUREMENT_PATTERN = re.compile(
      r"""
      (?<![a-zA-Z_])                         # Not part of an identifier
      (?P<sign>[-+−])?                       # Optional positive or negative sign
      (?P<value>\d+(?:\.\d+)?)               # Integer or decimal
      (?:\s*(?P<unit>                        # Optional measurement unit
          °[CF]|deg(?:rees)?(?:\s*[CF])?|%|percent|
          m[²23]|m³/day|m3/day|km[²2]|
          USD|INR|\$|₹
      ))?
      (?![a-zA-Z_])
      """,
      re.VERBOSE | re.IGNORECASE,
  )
  ```
- **Reproduction Command**:
  ```python
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from app.services.ai import validate_numeric_guardrails

  facts = {'prediction': {'suhii_c': 25.0, 'lst_c': 42.0}}
  text = 'Sentinel-2 captured 10m resolution imagery with Landsat-8 in 2024.'
  validate_numeric_guardrails(text, facts)
  "
  ```
- **Verbatim Error**:
  ```
  ValueError: Provider included unsupported numeric prose: 1
  ```
- **Direct Regex Inspection**:
  ```
  '10m'  -> Matches: ['1']
  '30m'  -> Matches: ['3']
  '100m' -> Matches: ['10']
  '250m' -> Matches: ['25']
  '15km' -> Matches: ['1']
  ```
- **Failure Cause**: `unit` does not include `m` (meters) or `km` (kilometers) alone; it only matches `m[²23]` and `km[²2]`. When matching `"10m"`, `\d+` matches `"10"`, but `(?![a-zA-Z_])` fails on `"m"`. The regex engine backtracks `\d+` to match `"1"`. The following character is `"0"`, which is not a letter, so lookahead succeeds! As a result, `"1"` is extracted as a standalone measurement, causing false-positive validation crashes whenever `1.0` is absent from facts.

#### Bug B: Scientific Notation Splitting
- **Direct Regex Inspection**:
  ```python
  NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3") -> ['1.8', '3']
  ```
- **Failure Cause**: The regex does not accommodate `[eE][-+]?\d+`. The lookahead `(?![a-zA-Z_])` triggers on `"e"`, causing backtracking to `"1.8"`, followed by matching `"3"` as an isolated integer.

#### Bug C: Fact Zero-Rounding Leakage / Bypassed Hallucination Guardrail
- **Code Reference**: `backend/app/services/ai.py:42, 72-75`
  ```python
  # ai.py:42
  found.add(int(round(val)))

  # ai.py:72-74
  is_supported = any(
      abs(raw_val - fn) < 0.15
      or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
      for fn in fact_numbers
  )
  ```
- **Reproduction Command**:
  ```python
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from app.services.ai import validate_numeric_guardrails

  facts = {'prediction': {'suhii_c': 5.0}, 'drivers': {'tree_canopy_pct': 0.2}}
  text = 'The model predicted cooling of 0.1°C.'
  validate_numeric_guardrails(text, facts)
  print('Hallucinated 0.1 deg C passed!')
  "
  ```
- **Result**: `Hallucinated 0.1 deg C passed!`
- **Failure Cause**: `tree_canopy_pct: 0.2` rounds via `int(round(0.2))` to `0`. `0` is added to `fact_numbers`. For any fabricated prose containing a number in `(-0.15, 0.15)` (e.g., `0.1°C`, `0.05%`), `abs(raw_val - 0) < 0.15` evaluates to `True`, allowing hallucinated statistics to bypass verification.

#### Bug D: In-Memory Rate Limiter Saturation in Multi-Suite Test Runs
- **Code Reference**: `backend/app/main.py:21, 60-65`
- **Output**: Running full suite `python -m pytest backend/tests` causes 31 tests in `test_e2e_tiers.py` and `test_foundation.py` to fail with `429 Too Many Requests` because the testclient makes >180 requests across test files in <60 seconds.

---

## 2. Logic Chain

1. **Spatial Robustness**:
   - Observations show that `assign_spatial_partitions()` correctly handles $N \in [5, 50+]$ zones, guards against $N < 5$, handles degenerate coordinate variance without division-by-zero, and extracts valid centroids from non-standard polygons.
   - Conclusion: The spatial partitioning implementation in `backend/app/services/ml.py` meets all milestone requirements and passes all empirical stress tests.

2. **AI Guardrail Correctness**:
   - The user dispatch explicitly specified: `Text containing valid domain numbers ("Sentinel-2 captured 10m resolution imagery with Landsat-8 in 2024")`.
   - Observation 1.2.A empirically proves that this exact sentence raises `ValueError: Provider included unsupported numeric prose: 1` whenever `1` is not in the fact context.
   - Observation 1.2.A proves that `\d+` backtracks before letters and splits numbers like `10m` into `1` and `0m`, and `30m` into `3` and `0m`.
   - Observation 1.2.C proves that `int(round(val))` inserts `0` into the fact number set whenever any fraction $< 0.5$ exists in the context, creating a 0.30-wide window $[-0.14, +0.14]$ where hallucinated statistics pass silently.
   - Conclusion: The regex pipeline in `backend/app/services/ai.py` suffers from both false-positive rejections of valid domain text and false-negative acceptance of small hallucinated statistics.

---

## 3. Caveats

- Streaming responses (`EventSourceResponse`) were not tested as the AI endpoint is currently implemented as unary JSON responses (`/api/ai/chat`).
- LLM API live calls were tested via mock handlers and direct unit validation of `validate_numeric_guardrails()` to avoid non-deterministic network and quota dependencies.
- The global in-memory rate limiter issue (`Bug D`) occurs only when running multiple large test suites in sequence; individual test modules pass when run separately.

---

## 4. Conclusion & Final Verdict

**VERDICT: REQUEST_CHANGES**

The spatial clustering enhancements in `backend/app/services/ml.py` are solid and approved. However, the AI guardrail in `backend/app/services/ai.py` requires remediation before Milestone 2 can be marked complete:

### Required Action Items for Worker M2:
1. **Fix Regex Backtracking and Add Metric Units**:
   - In `NUMERIC_MEASUREMENT_PATTERN`:
     - Prevent backtracking into digit sequences by requiring digits to be bounded by non-word/non-digit boundaries, e.g. using `(?<![a-zA-Z0-9_.])(?P<value>\d+(?:\.\d+)?)(?![0-9])`.
     - Include metric units `m`, `km`, `cm`, `mm`, `ha` in the unit regex or whitelist spatial resolutions (`10m`, `30m`, `60m`, `100m`, `250m`) in `ENTITY_WHITELIST`.
2. **Support Scientific Notation**:
   - Allow scientific exponent notation `(?:[eE][-+]?\d+)` in the value group so `1.85e-3` is treated as a single floating-point number.
3. **Prevent Zero-Rounding Fact Pollution**:
   - In `extract_numbers_from_facts()`, do not add `int(round(val))` when `abs(val) < 1.0` and `val != 0` (or only apply absolute tolerance when `fn != 0`).
4. **Test Suite Rate Limiter Reset**:
   - Add a pytest autouse fixture in `backend/tests/conftest.py` to clear `app.main.RATE` between tests or bypass the rate limiter when `TESTING=1`.

---

## 5. Verification Method

To independently reproduce and verify all findings:

1. **Run Challenger Test Suite**:
   ```bash
   python -m pytest backend/tests/test_challenger_m2.py -v
   ```
   *Expected*: All 27 tests pass, including tests proving backtracking (`test_regex_backtracking_vulnerability_on_unrecognized_units`), scientific notation splitting (`test_scientific_notation_mutilation`), and zero-rounding leakage (`test_zero_rounding_leakage`).

2. **Direct False-Positive Reproduction**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'backend'); from app.services.ai import validate_numeric_guardrails; validate_numeric_guardrails('Sentinel-2 captured 10m resolution imagery.', {'prediction': {'suhii_c': 25.0}})"
   ```
   *Expected*: `ValueError: Provider included unsupported numeric prose: 1`

3. **Direct False-Negative Reproduction**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'backend'); from app.services.ai import validate_numeric_guardrails; validate_numeric_guardrails('The microclimate cooled by 0.1°C.', {'drivers': {'tree_canopy_pct': 0.2}})"
   ```
   *Expected*: Completes without raising ValueError, proving hallucinated 0.1°C is accepted.
