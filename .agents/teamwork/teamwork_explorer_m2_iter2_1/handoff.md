# AI Guardrail Regex, Scientific Notation & Fact Rounding Remediation Blueprint

**Agent**: `teamwork_explorer_m2_iter2_1`  
**Role**: AI Guardrail Regex & Measurement Specialist (explorer, investigator, blueprint designer)  
**Date**: 2026-11-09  
**Target Milestone**: Milestone 2 Iteration 2 (AI Guardrail Robustness & Grounding)  
**Workspace**: `d:\Urban-Heat-Resilience-AI`  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1`  

---

## 1. Observation

Direct empirical investigation of `backend/app/services/ai.py` and `backend/tests/test_challenger_m2.py` reveals three distinct vulnerabilities in the numeric measurement guardrail pipeline:

### 1.1 Bug A: Catastrophic Regex Backtracking on Metric Units & Spatial Resolutions
- **Location**: `backend/app/services/ai.py:16-29`
- **Existing Implementation**:
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
  ```powershell
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from app.services.ai import validate_numeric_guardrails
  facts = {'prediction': {'suhii_c': 25.0, 'lst_c': 42.0}}
  text = 'Sentinel-2 captured 10m resolution imagery with Landsat-8 in 2024.'
  validate_numeric_guardrails(text, facts)
  "
  ```
- **Verbatim Error**:
  ```text
  ValueError: Provider included unsupported numeric prose: 1
  ```
- **Direct Regex Tracing**:
  ```python
  NUMERIC_MEASUREMENT_PATTERN.finditer("10m")  -> [('1', '1', None)]
  NUMERIC_MEASUREMENT_PATTERN.finditer("30m")  -> [('3', '3', None)]
  NUMERIC_MEASUREMENT_PATTERN.finditer("100m") -> [('10', '10', None)]
  NUMERIC_MEASUREMENT_PATTERN.finditer("250m") -> [('25', '25', None)]
  NUMERIC_MEASUREMENT_PATTERN.finditer("15km") -> [('1', '1', None)]
  ```
- **Mechanism of Failure**:
  1. For `"10m"`, the unit pattern only matches `m[²23]`, `m³/day`, `m3/day` — standalone `m` (meters) or `km` (kilometers) is completely omitted.
  2. The greedy group `(?P<value>\d+(?:\.\d+)?)` consumes `"10"`.
  3. The optional unit pattern fails to match `"m"`.
  4. The negative lookahead `(?![a-zA-Z_])` checks the character following `"10"`, which is `"m"`. Since `"m"` is an ASCII letter, the lookahead fails.
  5. The Python `re` backtracking engine backtracks `\d+` by one character, matching `"1"`.
  6. The character following `"1"` is `"0"`. Since `"0"` is not in `[a-zA-Z_]`, the lookahead `(?![a-zA-Z_])` unexpectedly succeeds!
  7. Consequently, `"1"` is emitted as an isolated measurement. When `1.0` is absent from facts, `validate_numeric_guardrails()` crashes with a false-positive `ValueError`.
  8. Furthermore, simple suffix checks like `(?!\d)` are insufficient: on decimal strings with unrecognized trailing letters (e.g. `"12.34xyz"`), `(?:\.\d+)?` backtracks by dropping the entire decimal component `".34"`, matching `"12"` because `"."` is not in `[a-zA-Z_]`.

---

### 1.2 Bug B: Scientific Notation Splitting & Hexadecimal Code Collisions
- **Location**: `backend/app/services/ai.py:20`
- **Reproduction**:
  ```python
  NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3") -> ['1.8', '3']
  ```
- **Mechanism of Failure**:
  1. The regex pattern `(?P<value>\d+(?:\.\d+)?)` lacks an exponential notation group `(?:[eE][-+]?\d+)`.
  2. On `"1.85e-3"`, `\d+(?:\.\d+)?` matches `"1.85"`.
  3. Lookahead `(?![a-zA-Z_])` encounters `"e"`, triggering backtracking: `\.\d+` gives up `"5"` to match `"1.8"`. Since `"5"` is not in `[a-zA-Z_]`, `"1.8"` is matched as the first number.
  4. The engine then encounters `"-3"`, matching `"3"` as a second isolated number.
  5. In addition, when adding `(?:[eE][-+]?\d+)`, a negative lookbehind restricted only to `(?<![a-zA-Z_])` allows hexadecimal color codes such as `#4A90E2` to match `'0E2'` as scientific notation ($0 \times 10^2 = 0$) because the character preceding `'0'` is `'9'`, which is not in `[a-zA-Z_]`. Therefore, the lookbehind MUST be hardened to `(?<![\w#])`.

---

### 1.3 Bug C: Fact Zero-Rounding Leakage Bypassing Hallucination Guardrail
- **Location**: `backend/app/services/ai.py:42, 72-75`
- **Existing Implementation**:
  ```python
  # ai.py:42 in extract_numbers_from_facts()
  found.add(int(round(val)))

  # ai.py:72-75 in validate_numeric_guardrails()
  is_supported = any(
      abs(raw_val - fn) < 0.15
      or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
      for fn in fact_numbers
  )
  ```
- **Reproduction Command**:
  ```powershell
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from app.services.ai import validate_numeric_guardrails
  facts = {'prediction': {'suhii_c': 5.0}, 'drivers': {'tree_canopy_pct': 0.2}}
  text = 'The model predicted cooling of 0.1°C.'
  validate_numeric_guardrails(text, facts)
  print('Hallucinated 0.1 deg C passed!')
  "
  ```
- **Verbatim Output**:
  ```text
  Hallucinated 0.1 deg C passed!
  ```
- **Mechanism of Failure**:
  1. Facts dictionaries frequently contain normalized fractions such as `tree_canopy_pct: 0.2`, `impervious_pct: 0.45`, or small SHAP values.
  2. `int(round(0.2))` and `int(round(0.45))` evaluate to `0`.
  3. `0` is added to `fact_numbers`.
  4. In `validate_numeric_guardrails()`, `abs(raw_val - fn) < 0.15` evaluates against `fn = 0` as `abs(raw_val) < 0.15`.
  5. Any fabricated number in $(-0.15, 0.15)$ (e.g. `0.1°C`, `0.05%`, `0.12°C`) matches `0` and passes without error, completely circumventing hallucination prevention.

---

## 2. Logic Chain

1. **Backtracking Elimination via Atomic Group Simulation**:
   - Standard Python `re` does not support possessive quantifiers (`\d++`) or atomic grouping `(?>...)`.
   - However, a lookahead assertion `(?=(pattern))\N` or `(?=(?P<name>pattern))(?P=name)` evaluates `pattern` once without allowing the engine to backtrack into sub-sequences when subsequent tokens fail.
   - Formulating the numeric literal as:
     ```python
     (?=(?P<value>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?))(?P=value)
     ```
     guarantees that once `\d+(?:\.\d+)?(?:[eE][-+]?\d+)?` greedily matches the full literal, it CANNOT yield characters or drop decimals.
   - If letters follow that do not match the unit pattern (e.g. `"10xyz"`, `"12.34xyz"`), the lookahead `(?![a-zA-Z_])` immediately fails and the entire match is discarded rather than slicing into `"1"`, `"10"`, or `"12"`.

2. **Standalone Metric Units & Spatial Resolution Entity Whitelisting**:
   - In `NUMERIC_MEASUREMENT_PATTERN`:
     - Longer units (`m³/day`, `m3/day`, `m[²23]`, `km[²2]`) must be positioned before shorter units (`m`, `km`) to prevent premature alternation termination (e.g. `m3/day` matching `m3` and leaving `/day`).
     - Adding `kilomet(?:ers?|res?)|km|centimet(?:ers?|res?)|cm|millimet(?:ers?|res?)|mm|hectares?|ha|m(?:eters?|etres?)?` ensures all standard SI units and full-word variations are parsed as valid measurement units.
   - In `ENTITY_WHITELIST`:
     - Satellite spatial resolution expressions (e.g. `10m`, `30m`, `60m`, `100m`, `250m`, `500m`, `1km`) describe sensor properties, not urban heat facts.
     - Adding `|(?:10|15|20|30|60|100|250|500|1000)[-\s]?m\b|\b[125][-\s]?km\b` to `ENTITY_WHITELIST` ensures sentences such as `"Sentinel-2 captured 10m resolution imagery with Landsat-8 in 2024."` are cleaned before numeric measurement auditing.

3. **Identifier & Hex Code Protection**:
   - Changing the lookbehind from `(?<![a-zA-Z_])` to `(?<![\w#])` ensures that:
     - Identifiers with embedded numbers (`model_v2_run3`, `feature_4`, `zone_01`, `cluster_id_9`) are not entered at digit positions.
     - Hexadecimal codes (`0x1A4F`, `#4A90E2`) do not trigger scientific notation false positives (`0E2`).

4. **Zero-Rounding Leakage Elimination**:
   - In `extract_numbers_from_facts()`:
     - Only add `int(round(val))` when `abs(val) >= 1.0`.
     - Small fractions ($0.0 < |val| < 1.0$) are added as `round(val, 2)` and `round(val, 1)` only, never rounded to `0`.
   - In `validate_numeric_guardrails()`:
     - In the grounding check, guard absolute tolerance against `fn == 0`:
       ```python
       is_supported = any(
           (abs(raw_val - fn) < 0.15 if fn != 0 else abs(raw_val) < 1e-6)
           or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
           for fn in fact_numbers
       )
       ```
     - Even if a fact genuinely contains `0.0` (e.g. `water_used: 0`), non-zero values such as `0.1` will not match `0.0`. Only genuine zeroes in prose (`raw_val == 0`) match.

---

## 3. Caveats

- **No Source Code Edits by Explorer**: In accordance with Explorer Archetype constraints, no source files were directly modified. Complete drop-in code is provided in `proposed_ai.py` and this handoff document for Worker M2.
- **Test File Synchronization**: Challenger M2-2 originally wrote lines 334-368 in `backend/tests/test_challenger_m2.py` to assert the *presence* of the bugs during Milestone 2 Iteration 1. Worker M2 must update these 3 test functions to assert the *remediated* behavior (see Section 4.2).

---

## 4. Conclusion & Complete Drop-In Remediation Blueprint

A complete, standalone drop-in replacement file has been authored and verified at:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\proposed_ai.py`

### 4.1 Targeted Patches for `backend/app/services/ai.py`

#### Patch 1: Entity Whitelist & Numeric Measurement Pattern
- **Target File**: `backend/app/services/ai.py`
- **Target Region**: Lines 8-29

```python
<<<<
# Whitelist benign domain entities with digits that must NOT trigger numeric audits
ENTITY_WHITELIST = re.compile(
    r"\b(?:Sentinel-[12345]|Landsat-[789]|MODIS|GHSL(?:-\d+)?|WorldCover|SRTM|WGS84|EPSG:\d+|PM(?:2\.5|10)|H3-\d+|ISO-\d+|COVID-19)\b",
    re.IGNORECASE,
)
ORDERED_LIST_MARKER = re.compile(r"(?:^|\n|\.\s+)\d+\.\s+")
YEAR_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b")

# Regex targeting physical measurements, percentages, ranges, and signed numbers
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
====
# Whitelist benign domain entities with digits that must NOT trigger numeric audits
ENTITY_WHITELIST = re.compile(
    r"\b(?:Sentinel-[12345]|Landsat-[789]|MODIS|GHSL(?:-\d+)?|WorldCover|SRTM|WGS84|EPSG:\d+|PM(?:2\.5|10)|H3-\d+|ISO-\d+|COVID-19"
    r"|(?:10|15|20|30|60|100|250|500|1000)[-\s]?m\b|\b[125][-\s]?km\b)\b",
    re.IGNORECASE,
)
ORDERED_LIST_MARKER = re.compile(r"(?:^|\n|\.\s+)\d+\.\s+")
YEAR_DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}(?:-\d{2}(?:-\d{2})?)?\b")

# Regex targeting physical measurements, percentages, ranges, and signed numbers
# Uses atomic group capture (?=(?P<value>...))(?P=value) to eliminate catastrophic backtracking into digits
NUMERIC_MEASUREMENT_PATTERN = re.compile(
    r"""
    (?<![\w#])                             # Not part of an identifier, hex code, or preceding digits
    (?P<sign>[-+−])?                       # Optional positive or negative sign
    (?=(?P<value>                          # Lookahead captures full numeric literal atomically
        \d+(?:\.\d+)?                      # Integer or decimal
        (?:[eE][-+]?\d+)?                  # Optional scientific exponent notation
    ))(?P=value)                           # Match captured value atomically without backtracking
    (?:\s*(?P<unit>                        # Optional measurement unit
        °[CF]|deg(?:rees)?(?:\s*[CF])?|%|percent|
        m³/day|m3/day|m[²23]|km[²2]|
        kilomet(?:ers?|res?)|km|centimet(?:ers?|res?)|cm|millimet(?:ers?|res?)|mm|hectares?|ha|m(?:eters?|etres?)?|
        USD|INR|\$|₹
    ))?
    (?![a-zA-Z_])                          # Unit or number must not be followed immediately by letters/underscore
    """,
    re.VERBOSE | re.IGNORECASE,
)
>>>>
```

---

#### Patch 2: Zero-Rounding Elimination in `extract_numbers_from_facts()`
- **Target File**: `backend/app/services/ai.py`
- **Target Region**: Lines 32-51

```python
<<<<
def extract_numbers_from_facts(facts):
    """Recursively collect all finite numeric values present in facts dictionary."""
    found = set()

    def _walk(obj):
        if isinstance(obj, (int, float)):
            if not isinstance(obj, bool) and np.isfinite(obj):
                val = float(obj)
                found.add(round(val, 2))
                found.add(round(val, 1))
                found.add(int(round(val)))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                _walk(v)

    _walk(facts)
    return found
====
def extract_numbers_from_facts(facts):
    """Recursively collect all finite numeric values present in facts dictionary."""
    found = set()

    def _walk(obj):
        if isinstance(obj, (int, float)):
            if not isinstance(obj, bool) and np.isfinite(obj):
                val = float(obj)
                found.add(round(val, 2))
                found.add(round(val, 1))
                # Only add integer-rounded values when magnitude >= 1.0 to prevent
                # zero-rounding leakage for small fractions (< 1.0)
                if abs(val) >= 1.0:
                    found.add(int(round(val)))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                _walk(v)

    _walk(facts)
    return found
>>>>
```

---

#### Patch 3: Grounding Tolerance Hardening in `validate_numeric_guardrails()`
- **Target File**: `backend/app/services/ai.py`
- **Target Region**: Lines 70-76

```python
<<<<
        # Grounding check: number must match a known fact in context
        is_supported = any(
            abs(raw_val - fn) < 0.15
            or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
            for fn in fact_numbers
        )
====
        # Grounding check: number must match a known fact in context
        # fn == 0 requires raw_val == 0 (within float epsilon 1e-6) to prevent zero-rounding bypass
        is_supported = any(
            (abs(raw_val - fn) < 0.15 if fn != 0 else abs(raw_val) < 1e-6)
            or (fn != 0 and abs(raw_val - fn) / abs(fn) < 0.05)
            for fn in fact_numbers
        )
>>>>
```

---

### 4.2 Test Regression Updates for `backend/tests/test_challenger_m2.py`
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
        assert matches_10m == ["10m"]

        matches_30m = [m.group(0) for m in NUMERIC_MEASUREMENT_PATTERN.finditer("30m")]
        assert "3" not in matches_30m
        assert matches_30m == ["30m"]

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

To independently verify the blueprint:

1. **Execute 15-Point Empirical Verification Battery**:
   ```powershell
   python -c "
   import sys; sys.path.insert(0, 'backend')
   import importlib.util
   spec = importlib.util.spec_from_file_location('proposed_ai', r'd:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_iter2_1\proposed_ai.py')
   ai = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(ai)

   # 1. Backtracking check
   assert [m.group(0) for m in ai.NUMERIC_MEASUREMENT_PATTERN.finditer('10m')] == ['10m']
   assert [m.group(0) for m in ai.NUMERIC_MEASUREMENT_PATTERN.finditer('30m')] == ['30m']
   assert [m.group(0) for m in ai.NUMERIC_MEASUREMENT_PATTERN.finditer('10xyz')] == []

   # 2. Scientific notation check
   assert [m.group(0) for m in ai.NUMERIC_MEASUREMENT_PATTERN.finditer('1.85e-3')] == ['1.85e-3']

   # 3. Whitelist imagery check
   ai.validate_numeric_guardrails('Sentinel-2 captured 10m resolution imagery.', {'prediction': {'suhii_c': 25.0}})

   # 4. Zero rounding leakage check
   mock_facts = {'prediction': {'suhii_c': 3.42}, 'drivers': {'impervious_pct': 0.45}}
   try:
       ai.validate_numeric_guardrails('The microclimate cooled by 0.1°C.', mock_facts)
       assert False, 'Should have blocked hallucinated 0.1°C'
   except ValueError as e:
       assert '0.1°C' in str(e)

   print('ALL BLUEPRINT VERIFICATION CHECKS PASSED!')
   "
   ```
   *Expected Output*: `ALL BLUEPRINT VERIFICATION CHECKS PASSED!`

2. **Run Pytest against Proposed Module**:
   Once Worker M2 applies the patches to `backend/app/services/ai.py` and `backend/tests/test_challenger_m2.py`:
   ```powershell
   python -m pytest backend/tests/test_challenger_m2.py backend/tests/test_ai.py -v
   ```
   *Expected Output*: All 28 tests pass (27 challenger tests + 1 AI provider test).

3. **Invalidation Conditions**:
   - `NUMERIC_MEASUREMENT_PATTERN.finditer("10m")` extracting `"1"`.
   - `NUMERIC_MEASUREMENT_PATTERN.finditer("1.85e-3")` splitting into multiple tokens.
   - `validate_numeric_guardrails("The microclimate cooled by 0.1°C.", mock_facts)` failing to raise `ValueError`.
   - `validate_numeric_guardrails("Sentinel-2 captured 10m resolution imagery.", facts_without_1)` raising `ValueError`.
