## 2026-11-09T13:53:55Z
You are AGENT 3: Machine Learning and Spatial XAI Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_ml_m3\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Your exclusive write ownership:
- `backend/app/services/features.py` (create)
- `backend/app/services/xai.py` (create)
- `backend/app/services/ml.py` (enhance and refactor to use features.py and xai.py)
- `backend/tests/test_ml_xai.py` (create or update)

Tasks:
1. Feature Engineering in `backend/app/services/features.py`:
   - Define canonical FEATURES configuration.
   - Enforce strict anti-leakage: geographic coordinates (`lat`, `lon`, `row`, `column`, `spatial_block`) and target-derived variables (`lst`, `observed_suhii`, `rural_reference`) MUST NEVER be included in feature matrix X.
   - Implement robust missing-data imputation (median imputer fitted strictly on training partition).
2. Spatial Cross-Validation & Anti-Leakage:
   - 6-block spatial separation along primary spatial dispersion axis.
   - Block 4 MUST act as an explicit spatial buffer fold completely withheld from training, validation, and testing to prevent spatial autocorrelation leakage.
   - Generalized spatial partitioning for arbitrary geometry via 2D spatial KMeans / spatial quantiles.
3. Model Tournament & Persistence:
   - Competitive tournament across Random Forest, XGBoost, and LightGBM.
   - Winner selected by lowest validation RMSE.
   - Save and load trained models via joblib with caching.
   - Track evaluation metrics: R², RMSE, MAE for both validation and test partitions.
   - Empirical prediction intervals from validation residuals.
4. Exact Additive TreeSHAP & Spatial XAI in `backend/app/services/xai.py`:
   - Local explanations per zone: exact additive TreeSHAP where `shap_base + sum(shap) == predicted_suhii` (additivity error < 1e-4).
   - Global feature importance ranked by mean absolute SHAP value.
   - Geographical visualization of local SHAP contributions across zones.
   - Comparison of heat-driving factors across locations.
5. External Validation & Strict Separation:
   - Clearly separate synthetic benchmark performance metrics from real-world observation metrics in data structures and reporting.
   - Never claim real-world accuracy on synthetic test partitions.
6. Write tests in `backend/tests/test_ml_xai.py` and run `pytest`. Ensure 0 regressions.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_ml_m3\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method with exact test execution results.
When done, message the orchestrator.
