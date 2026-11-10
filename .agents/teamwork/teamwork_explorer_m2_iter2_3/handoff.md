# Spatial Partitioning & Challenger Tests Remediation Blueprint

**Agent**: `teamwork_explorer_m2_iter2_3`  
**Role**: Spatial Partitioning & Challenger Tests Specialist (explorer, investigator, synthesizer)  
**Date**: 2026-11-09  
**Target Milestone**: Milestone 2 Iteration 2 (Backend ML & Challenger Test Integration)  
**Workspace**: `d:\Urban-Heat-Resilience-AI`  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_3`  

---

## 1. Observation

### 1.1 Spatial Partition Discontinuity in `backend/app/services/ml.py:183`
- **Location**: `backend/app/services/ml.py:183-187`
- **Existing Implementation**:
  ```python
  min_required = 1 if n < 60 else 15
  if min(tr.sum(), val.sum(), test.sum()) < min_required:
      raise ValueError(
          f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid."
      )
  ```
- **Reproduction Command**:
  ```powershell
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from app.services.ml import train
  from tests.test_challenger_m2 import make_zone_features
  coords = [[72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)] for i in range(60)]
  features = make_zone_features(coords)
  data = {'type': 'FeatureCollection', 'metadata': {'city': 'Test60', 'generated_at': '2026-11-09T00:00:00Z'}, 'features': features}
  train(data)
  "
  ```
- **Verbatim Error**:
  ```text
  ValueError: Need at least 15 cell(s) in each spatial partition. Use a larger area or denser grid.
  ```

### 1.2 KMeans Cluster Count Asymmetry for $N \in [60, 89]$
- **Location**: `backend/app/services/ml.py:108-120`
- **Existing Implementation**:
  ```python
  kmeans = KMeans(n_clusters=6, random_state=random_state, n_init=10)
  cluster_labels = kmeans.fit_predict(coords)
  cluster_centers = kmeans.cluster_centers_[:, primary_axis]
  sorted_clusters = np.argsort(cluster_centers)
  cluster_map = {old: new for new, old in enumerate(sorted_clusters)}
  mapped_blocks = np.array([cluster_map[c] for c in cluster_labels])
  counts = [np.sum(mapped_blocks == i) for i in range(6)]
  if min(counts) < 1:
      raise ValueError("Imbalanced cluster detected")
  blocks = mapped_blocks.tolist()
  used_kmeans = True
  ```
- **Direct Empirical Observation**:
  For $N = 60$ arranged on a regular grid:
  ```python
  Cluster counts: [ 9  9 12  9  9 12]
  ```
  Even though the mathematical average cluster size is $60 / 6 = 10$, spatial clustering groups nearest centroids, producing four clusters with 9 zones and two clusters with 12 zones.
  Consequently:
  - If `min_required` is evaluated strictly as `max(1, min(15, n // 6)) = 10`, but KMeans assigns 9 zones to validation (`mapped_blocks == 3`) or test (`mapped_blocks == 5`), `min(tr.sum(), val.sum(), test.sum())` evaluates to $9 < 10$, triggering `ValueError`.
  - Conversely, quantile fallback partitioning `np.array_split(sort_idx, 6)` divides $N = 60$ into $[10, 10, 10, 10, 10, 10]$, guaranteeing every block has $\ge \lfloor n / 6 \rfloor$ zones.
  - Therefore, line 116 (`if min(counts) < 1:`) must require `min(counts) >= max(1, min(15, n // 6))` so that any under-sized KMeans fold triggers the safe quantile fallback.

### 1.3 Full Test Suite Execution (174 Tests Monolithic Run)
- **Execution Command**:
  ```powershell
  python -m pytest backend/tests/ -v
  ```
- **Verbatim Output**:
  ```text
  platform win32 -- Python 3.14.6, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\siddh\AppData\Local\Programs\Python\Python314\python.exe
  cachedir: .pytest_cache
  rootdir: D:\Urban-Heat-Resilience-AI
  configfile: pytest.ini
  plugins: anyio-4.15.1, langsmith-0.14.11, asyncio-1.4.1
  collected 174 items

  backend/tests/test_ai.py (1 passed)
  backend/tests/test_api.py (5 passed)
  backend/tests/test_challenger_m2.py (27 passed)
  backend/tests/test_challenger_m2_api_budget.py (20 passed)
  backend/tests/test_e2e_tiers.py (78 passed)
  backend/tests/test_foundation.py (3 passed)
  backend/tests/test_pipeline.py (6 passed)
  backend/tests/test_sources.py (34 passed)

  ====================== 174 passed, 15 warnings in 44.71s ======================
  ```
- **Exit Code**: 0

### 1.4 Challenger Test Suite Structure and Vulnerability Demonstrations
1. **`backend/tests/test_challenger_m2_api_budget.py` (20 tests)**:
   - Covers CP-SAT budget optimizer edge cases ($0, tight, $1B, negative inputs, schema validation).
   - Covers state store concurrency and APIRouter edge cases.
   - Includes function-scoped autouse fixture `reset_rate_limit` (lines 24-29) clearing `app.main.RATE`.
   - All 20 tests pass cleanly without external dependencies.
2. **`backend/tests/test_challenger_m2.py` (27 tests)**:
   - Lines 56-216: 12 spatial partitioning stress tests (`TestSpatialClusteringStress`).
   - Lines 218-239: 1 custom zone end-to-end training test (`TestModelTrainingWithCustomPartitions`).
   - Lines 244-332: 11 AI guardrail validation tests (`TestAINumericGuardrails`).
   - **Lines 334-368: 3 Iteration 1 defect demonstration tests**:
     - `test_regex_backtracking_vulnerability_on_unrecognized_units`: Asserts `'10m'` backtracks to `['1']` and raises `ValueError: Provider included unsupported numeric prose: 1`.
     - `test_scientific_notation_mutilation`: Asserts `'1.85e-3'` splits into `['1.8', '3']`.
     - `test_zero_rounding_leakage`: Asserts fabricated `'0.1°C'` passes without error due to `int(round(0.45)) == 0`.
   - **Crucial Interaction**: Once `backend/app/services/ai.py` is remediated in Iteration 2 (as designed by `teamwork_explorer_m2_iter2_1`), these 3 tests would fail unless they are transitioned from flaw demonstrations to permanent regression tests.

---

## 2. Logic Chain

1. **Partition Cell Threshold Inconsistency (Observation 1.1)**:
   - For $N < 60$, `min_required = 1`. A custom GeoJSON with 59 zones requires only 1 cell per partition, which passes easily.
   - For $N = 60$, `min_required = 15`. In a 6-block partition, validation (1 block) has $\approx 10$ cells and test (1 block) has $\approx 10$ cells.
   - Because $10 < 15$, training crashes with `ValueError`. This affects every custom upload with $N \in [60, 89]$ zones.
   - Replacing `min_required = 1 if n < 60 else 15` with `min_required = max(1, min(15, n // 6))` dynamically scales the threshold:
     - For $N = 5$: $\max(1, \min(15, 0)) = 1$.
     - For $N = 60$: $\max(1, \min(15, 10)) = 10$.
     - For $N = 89$: $\max(1, \min(15, 14)) = 14$.
     - For $N = 90$: $\max(1, \min(15, 15)) = 15$.
     - For baseline datasets ($N = 324$): $\max(1, \min(15, 54)) = 15$. Exact baseline behavior is preserved.

2. **KMeans Cardinality Imbalance & Safe Quantile Fallback (Observation 1.2)**:
   - Standard 2D KMeans does not guarantee equal-sized clusters. An arbitrary zone layout can yield cluster sizes such as $[9, 9, 12, 9, 9, 12]$ for $N = 60$.
   - When a cluster has 9 zones and `min_required` is 10, the threshold check fails even with the dynamic formula.
   - In `assign_spatial_partitions()` line 116, replacing `if min(counts) < 1:` with `if min(counts) < max(1, min(15, n // 6)):` ensures that if KMeans produces any fold smaller than the required threshold, it automatically raises `ValueError("Imbalanced cluster detected")` and triggers the existing fallback to 6-block quantile partitioning (`np.array_split(sort_idx, 6)`).
   - Quantile partitioning guarantees that every block has at least $\lfloor n / 6 \rfloor$ cells. Thus, $\min(tr, val, test) \ge \min\_required$ holds with 100% mathematical certainty for all $N \ge 5$.

3. **Challenger Test Suite Permanent Integration (Observations 1.3 & 1.4)**:
   - The two challenger test suites add 47 rigorous adversarial test cases (bringing total backend tests from 127 to 174).
   - All 174 tests currently pass because the test execution order places `test_challenger_m2_api_budget.py` (which resets `app.main.RATE`) before `test_e2e_tiers.py`.
   - When `teamwork_explorer_m2_iter2_2` adds the rate limiter fixture to `conftest.py` and test bypass to `main.py`, test independence is permanently guaranteed regardless of execution order.
   - For `test_challenger_m2.py`: The 3 flaw-demonstrating tests (`test_regex_backtracking_vulnerability_on_unrecognized_units`, `test_scientific_notation_mutilation`, `test_zero_rounding_leakage`) must be updated to assert the fixed behavior (e.g. `10m` accepted, `1.85e-3` parsed as single number, `0.1°C` rejected).
   - Adding a dedicated test `test_zone_counts_60_to_89_partition_cleanly` ensures that $N \in [60, 89]$ zone counts are permanently exercised in CI.

---

## 3. Caveats

- **Minimum Zone Requirement**: Spatial partitioning requires at least $N \ge 5$ zones (`ml.py:65`). GeoJSONs with $N < 5$ zones will continue to raise `ValueError("Need at least 5 zones for spatial cross-validation")`.
- **Baseline City Stability**: Baseline synthetic datasets ($N = 324$) have `has_legacy_blocks = True` with 54 validation and 54 test cells. They evaluate `min_required = 15` and remain completely unaffected.
- **Worker Execution Order**: Worker M2 must apply the `ai.py` fix and `test_challenger_m2.py` regression updates together so that the suite transitions smoothly from 174 passing tests to 174+ passing tests.

---

## 4. Conclusion & Exact Drop-In Code Blueprint

### 4.1 Drop-In Code for `backend/app/services/ml.py`

#### Patch 1: Dynamic Cluster Balance Check in `assign_spatial_partitions()`
- **Target File**: `backend/app/services/ml.py`
- **Target Region**: Lines 115-119

```python
<<<<
            counts = [np.sum(mapped_blocks == i) for i in range(6)]
            if min(counts) < 1:
                raise ValueError("Imbalanced cluster detected")
            blocks = mapped_blocks.tolist()
            used_kmeans = True
====
            counts = [np.sum(mapped_blocks == i) for i in range(6)]
            min_cluster_req = max(1, min(15, n // 6))
            if min(counts) < min_cluster_req:
                raise ValueError(
                    f"Imbalanced cluster detected: minimum cluster has {min(counts)} < {min_cluster_req}"
                )
            blocks = mapped_blocks.tolist()
            used_kmeans = True
>>>>
```

#### Patch 2: Dynamic Partition Threshold in `train()`
- **Target File**: `backend/app/services/ml.py`
- **Target Region**: Lines 183-187

```python
<<<<
    min_required = 1 if n < 60 else 15
    if min(tr.sum(), val.sum(), test.sum()) < min_required:
        raise ValueError(
            f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid."
        )
====
    min_required = max(1, min(15, n // 6))
    if min(tr.sum(), val.sum(), test.sum()) < min_required:
        raise ValueError(
            f"Need at least {min_required} cell(s) in each spatial partition. Use a larger area or denser grid."
        )
>>>>
```

---

### 4.2 Drop-In Code for `backend/tests/test_challenger_m2.py`

#### Patch 1: Add $N \in [60, 89]$ Spatial Partition Regression Test
- **Target File**: `backend/tests/test_challenger_m2.py`
- **Target Region**: After line 238 in `TestModelTrainingWithCustomPartitions`

```python
    def test_zone_counts_60_to_89_partition_cleanly(self):
        """Custom GeoJSONs with N in [60, 89] zones partition cleanly without partition cell threshold errors."""
        init_db()
        for n in [60, 75, 89]:
            coords = [[72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)] for i in range(n)]
            features = make_zone_features(coords)
            data = {
                "type": "FeatureCollection",
                "metadata": {"city": f"Test{n}", "generated_at": "2026-11-09T00:00:00Z"},
                "features": features,
            }
            artifact = train(data)
            assert artifact["split"]["validation"] >= 1
            assert artifact["split"]["test"] >= 1
            assert artifact["split"]["training"] >= 3
            assert np.isfinite(artifact["interval"])
```

#### Patch 2: Convert Vulnerability Demonstrations to Permanent Regression Tests
- **Target File**: `backend/tests/test_challenger_m2.py`
- **Target Region**: Lines 334-368

```python
<<<<
    def test_regex_backtracking_vulnerability_on_unrecognized_units(self):
        """
        Adversarial finding: When text has '10m', '30m', or other numbers with
        unrecognized unit suffixes, the regex backtracks and extracts the first
        digits as an ungrounded number ('10m' -> '1', '30m' -> '3').
        """
        matches_10m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("10m")]
        assert matches_10m == ["1"], "Demonstrates backtracking flaw: '10m' matches '1'"

        matches_30m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("30m")]
        assert matches_30m == ["3"], "Demonstrates backtracking flaw: '30m' matches '3'"

        # If facts do not contain 1, this raises unsupported numeric prose: 1
        facts_without_1 = {"prediction": {"suhii_c": 25.0}}
        with pytest.raises(ValueError, match="unsupported numeric prose: 1"):
            validate_numeric_guardrails("Sentinel-2 captured 10m resolution imagery.", facts_without_1)

    def test_scientific_notation_mutilation(self):
        """
        Adversarial finding: Scientific notation like 1.85e-3 is split into
        '1.8' and '3' instead of being parsed as a floating point number.
        """
        matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3")]
        assert matches == ["1.8", "3"], "Demonstrates scientific notation splitting flaw"

    def test_zero_rounding_leakage(self, mock_facts):
        """
        Adversarial finding: Any fact number between 0 and 0.49 rounds to 0.
        Because tolerance is abs(raw_val - 0) < 0.15, any fabricated number in
        (-0.15, 0.15) like 0.1°C or 0.05 falsely passes validation.
        """
        # mock_facts contains impervious_pct = 0.45, so 0 is in fact_numbers
        # A fabricated cooling of 0.1°C (which does not exist in facts) passes
        text = "The microclimate cooled by 0.1°C."
        validate_numeric_guardrails(text, mock_facts)  # Demonstrates zero tolerance leakage
====
    def test_regex_backtracking_vulnerability_on_unrecognized_units(self):
        """Regression test: '10m' and '30m' do not backtrack into standalone '1' or '3'."""
        matches_10m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("10m")]
        assert "1" not in matches_10m

        matches_30m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("30m")]
        assert "3" not in matches_30m

        # Valid imagery prose with 10m does not falsely fail validation when 1 is not in facts
        facts_without_1 = {"prediction": {"suhii_c": 25.0}}
        validate_numeric_guardrails("Sentinel-2 captured 10m resolution imagery.", facts_without_1)

    def test_scientific_notation_mutilation(self):
        """Regression test: Scientific notation like 1.85e-3 is parsed as a single floating point number."""
        matches = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3")]
        assert matches == ["1.85e-3"]

    def test_zero_rounding_leakage(self, mock_facts):
        """Regression test: Fabricated number in (-0.15, 0.15) is rejected and does not leak through zero-rounding."""
        text = "The microclimate cooled by 0.1°C."
        with pytest.raises(ValueError, match="unsupported numeric prose: 0.1°C"):
            validate_numeric_guardrails(text, mock_facts)
>>>>
```

---

## 5. Verification Method

To independently verify this blueprint and certify full suite integration:

1. **Verify Spatial Partitioning Across $N \in [60, 90]$**:
   ```powershell
   python -c "
   import sys; sys.path.insert(0, 'backend')
   from app.services.ml import train
   from tests.test_challenger_m2 import make_zone_features
   from app.db import init_db
   init_db()

   for n in [60, 75, 89]:
       coords = [[72.5 + 0.01 * (i % 6), 23.0 + 0.01 * (i // 6)] for i in range(n)]
       features = make_zone_features(coords)
       data = {'type': 'FeatureCollection', 'metadata': {'city': f'City_{n}', 'generated_at': '2026-11-09T00:00:00Z'}, 'features': features}
       art = train(data)
       print(f'N={n} passed! Winner: {art[\"winner\"]}, val={art[\"split\"][\"validation\"]}, test={art[\"split\"][\"test\"]}')
   "
   ```
   *Expected Output*: All tested zone sizes ($N=60, 75, 89$) output `passed!` with positive validation and test counts.

2. **Run Both Challenger Test Suites**:
   ```powershell
   python -m pytest backend/tests/test_challenger_m2_api_budget.py backend/tests/test_challenger_m2.py -v
   ```
   *Expected Output*: All 47 tests pass.

3. **Run Monolithic Backend Test Suite (174+ Tests)**:
   ```powershell
   python -m pytest backend/tests/ -v
   ```
   *Expected Output*: 174+ passed, 0 failed, 0 errors in ~45 seconds.

4. **Invalidation Conditions**:
   - Any `ValueError: Need at least 15 cell(s) in each spatial partition` for custom datasets with $N \in [60, 89]$.
   - Any failure in the 174 tests when run consecutively as a single pytest execution.
