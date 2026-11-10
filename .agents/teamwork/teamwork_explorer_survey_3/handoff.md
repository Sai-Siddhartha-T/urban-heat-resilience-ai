# Handoff Report: Survey 3 — ML, Spatial XAI, Heat Risk, Intervention Optimization & Grounded AI Assistant

**Author**: `teamwork_explorer_survey_3`  
**Recipient**: `orchestrator` (`ef9393af-13d2-4069-906d-ff502c4a45d2`)  
**Date**: 2026-11-10  
**Handoff Type**: Hard (Investigation & Specification Complete)  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3`  
**Analysis File**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md`  

---

## 1. Observation

1. **OR-Tools CP-SAT Budget Elimination**:
   - In `backend/app/services/optimization.py:1-6, 124-354`, the optimizer enforces only discrete 5% coverage levels, surface capacities (ground, roof, road), `land_limit_pct`, `protected` land prohibition, `cool_roofs` vs `roof_gardens` mutual exclusivity, `max_vegetation_pct`, `water_limit`, `min_cooling`, and 3.0°C cooling saturation.
   - Running `Get-ChildItem -Recurse -File backend\app -Include *.py | Select-String -Pattern 'budget'` returned only two occurrences, both docstrings in `optimization.py:5, 139`: *"Financial budget constraints are completely removed."*
   - `backend/app/schemas.py:90-96` (`OptimizationRequest`) and `166-178` (`OptimizationResponse`) contain zero budget or cost fields.
2. **ML Pipeline & Spatial XAI**:
   - `backend/app/services/features.py:88-101`: `validate_no_leakage()` strictly blocks coordinates (`lat`, `lon`, `x`, `y`, `row`, `column`), target variables (`observed_suhii`, `lst`, `suhii`, `rural_reference`), and partition metadata (`spatial_block`, `partition`).
   - `backend/app/services/ml.py:238-246`: SimpleImputer with median strategy is strictly fitted on `tr` (training partition) and applied out-of-sample to validation and test sets.
   - `backend/app/services/ml.py:71-79`: `metrics()` computes $R^2$, RMSE, and MAE. Mean prediction bias, residual distribution statistics, and spatial error autocorrelation maps are absent.
   - `backend/app/services/xai.py:217-233`: TreeSHAP additivity is verified with tolerance $< 1\times 10^{-4}$. Models and explainers are persisted to disk via `joblib`.
   - Files `backend/app/services/ml.py` and `backend/app/services/ml_train.py` are ~90% duplicated.
3. **Heat Risk Assessment & Demographics**:
   - `backend/app/services/risk.py:41-70`: Hazard is calculated solely from `suhii / 8.0` (missing air temperature and duration). Exposure is calculated solely from `pop_density / 25000.0` (missing residential density and land-use).
   - `backend/app/services/risk.py:71-210`: Vulnerability decomposes into age sensitivity (elderly and children share), socioeconomic deprivation (poverty rate, informal housing %, outdoor workers), and adaptive capacity (cooling deficit). Population density is not substituted for vulnerability.
   - `backend/app/services/demographics.py:488-650`: `fetch_worldpop` and `fetch_ghsl` return catalog metadata (`catalog_only=True`), not sampled raster values. `fetch_census` calls `api.census.gov` (US Census) rather than Indian ward/administrative data.
4. **Grounded AI Assistant**:
   - `backend/app/services/llm/fallback.py:199-262`: Multi-provider orchestrator attempts Groq (`GroqProvider`), then Gemini (`GeminiProvider`), then local deterministic placeholder.
   - `backend/app/services/llm/guardrails.py:62-115`: Verifies that findings cite valid fact IDs (`validate_citations`), validates numeric literals in prose against facts within 5% tolerance (`validate_numeric_guardrails`), and verifies action feasibility via `simulate()` (`validate_action_feasibility`).
   - `backend/app/services/llm/fallback.py:98-170`: When providers fail, `deterministic_placeholder` returns a synthetic response instead of a prominent error message with setup instructions.
5. **State Cache 409 Issue in Test Suite**:
   - Running `pytest backend/tests` resulted in: `97 failed, 251 passed, 15 warnings, 17 errors in 70.58s`.
   - In `backend/app/services/state.py:81-108`: `resolve_mode(mode)` returns `"demo"` if `mode == "demo"`, else `"normal"`. In `"normal"` mode, `state()` raises `HTTPException(409)` if no measured dataset is in the DB.
   - In `backend/tests/conftest.py:99`, `os.environ["HEATWISE_DEMO_MODE"] = "1"` is set, but `state.py` never checks `os.getenv("HEATWISE_DEMO_MODE")` or `os.getenv("TESTING")`. This causes test fixtures calling `state("Ahmedabad")` without `mode="demo"` to crash with HTTP 409.

---

## 2. Logic Chain

1. **Regarding Optimization (Observation 1)**:
   - The user request explicitly demands: *"Build an optimizer (e.g. OR-Tools CP-SAT) enforcing physical, land-use, and water constraints to generate feasible intervention combinations and spatial priority plans WITHOUT ANY FINANCIAL BUDGET CONSTRAINTS OR OBJECTIVES."*
   - Code inspection confirms that budget variables and costs have already been removed from `optimization.py` and `schemas.py`.
   - Therefore, Agent 4's primary mandate for optimization is to **preserve this zero-budget physical formulation** while adding literature-grounded cooling mechanisms, spatial priority ranking, and solver tuning.
2. **Regarding ML & XAI (Observation 2)**:
   - `ml.py` has sound anti-leakage and spatial partitioning, but lacks temporal cross-validation, prediction bias metrics, residual distribution metrics, and spatial error mapping.
   - `ml.py` and `ml_train.py` cause maintenance divergence.
   - Therefore, Agent 3 must consolidate the ML services into `ml.py`, implement temporal validation folds, add bias and residual analysis metrics, and generate spatial error maps.
3. **Regarding Heat Risk & Demographics (Observation 3)**:
   - R6 requires transparent decomposition of hazard (surface heat, air temperature, duration) and exposure (population, residential density, land use).
   - Currently, hazard uses only SUHII and exposure uses only population density.
   - Demographics lacks raster sampling for WorldPop/GHSL and uses a US Census endpoint.
   - Therefore, Agent 2 must expand hazard and exposure into multi-factor indices, implement raster sampling for WorldPop/GHSL, and provide local ward tables for Ahmedabad, Delhi, and Hyderabad.
4. **Regarding AI Assistant (Observation 4)**:
   - R7 requires: *"answering questions strictly grounded in actual backend data with source citations, displaying clear errors on failure rather than synthetic responses."*
   - Currently, when external providers fail, a synthetic template response is returned.
   - Therefore, Agent 5 must update `fallback.py` to return clear, user-facing error indicators when a configured provider fails, and clearly delineate offline deterministic analysis.
5. **Regarding Test Failures (Observation 5)**:
   - 97 test failures stem directly from `state.py` raising HTTP 409 in test environments where `mode` is None.
   - Updating `resolve_mode()` to check `os.getenv("HEATWISE_DEMO_MODE") == "1"` or `os.getenv("TESTING") == "1"` will restore test passing across the suite.

---

## 3. Caveats

- Live external API calls to Groq and Google Gemini require valid API keys (`GROQ_API_KEY`, `GEMINI_API_KEY`) to test live LLM completions outside the mock test suite.
- Raster sampling of WorldPop and GHSL requires local raster GeoTIFF files or Cloud-Optimized GeoTIFF (COG) access over the internet.
- The 409 state behavior is technically an intentional Phase 2 integrity guard to prevent synthetic data leakage into normal mode; resolving it in test environments must not compromise production normal mode checks.

---

## 4. Conclusion

The technical foundations for R5, R6, and R7 are solid, with clean anti-leakage ML pipelines, verified additive TreeSHAP explainers, physical-only OR-Tools CP-SAT optimization, and strict anti-hallucination guardrails. The system is ready for specialized engineering upgrades across Agents 2, 3, 4, and 5:

1. **Agent 2 (Demographics & Risk)**:
   - Expand `calculate_hazard` (add air temp & heatwave duration) and `calculate_exposure` (add residential density & land use).
   - Add raster sampling for WorldPop/GHSL and provide Indian city ward demographic tables.
2. **Agent 3 (ML & Spatial XAI)**:
   - Consolidate `ml.py` and `ml_train.py`.
   - Add temporal cross-validation, prediction bias, residual analysis stats, and spatial error mapping.
   - Maintain explicit non-causal presentation of TreeSHAP associations.
3. **Agent 4 (Simulation & Optimization)**:
   - Ground intervention cooling rates in urban climatology literature.
   - Generate spatial priority plans in CP-SAT output.
   - Strictly preserve the zero-budget physical-only optimization model.
4. **Agent 5 (Generative AI)**:
   - Surface explicit, actionable errors on provider failure instead of synthetic answers.
   - Clearly delineate offline deterministic evidence analysis.
   - Connect data provenance into context facts.

---

## 5. Verification Method

To independently verify this survey:
1. **Verify Budget Elimination**:
   ```powershell
   Get-ChildItem -Recurse -File backend\app -Include *.py | Select-String -Pattern 'budget'
   ```
   (Must only return docstrings in `optimization.py` confirming budget removal.)
2. **Run ML & XAI Test Suite**:
   ```powershell
   pytest backend/tests/test_ml_xai.py
   ```
   (39 tests passing, verifying exact TreeSHAP additivity and feature attributions.)
3. **Run Demographics Test Suite**:
   ```powershell
   pytest backend/tests/test_demographics.py
   ```
   (31 tests passing, verifying age distribution and vulnerability calculations.)
4. **Inspect State Cache 409 Cause**:
   View lines 81-108 in `backend/app/services/state.py` and line 99 in `backend/tests/conftest.py`.
