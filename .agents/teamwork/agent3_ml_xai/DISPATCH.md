## 2026-11-10T12:29:36Z
You are specialized AGENT 3: Machine Learning and Spatial XAI Engineer working on Milestone M3 (Defensible ML, Climate Analytics & Explainable AI) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent3_ml_xai
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_3\handoff.md` first.
Your exclusive file ownership:
- `backend/app/services/ml.py`
- `backend/app/services/features.py`
- `backend/app/services/xai.py`
- `backend/tests/test_ml_xai.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R5):
1. Target Variable Definition & Service Consolidation:
   - Explicitly define prediction targets: Land Surface Temperature (LST in °C) and Surface Urban Heat Island Intensity (SUHII in °C relative to rural reference). Differentiate clearly from air temperature.
   - Consolidate duplicated logic from `ml_train.py` into `ml.py`.
2. Anti-Leakage Feature Pipeline:
   - Preserve and enforce `validate_no_leakage()` in `features.py`. Train-only SimpleImputer fitting to prevent data leakage.
3. Spatial and Temporal Validation:
   - In `ml.py`, support both spatial cross-validation (KMeans coordinate clustering / block splits) and temporal cross-validation (time-series splits across multi-date acquisitions or seasonal periods) to prevent spatial/temporal leakage.
4. Model Tournament:
   - Compare Random Forest, XGBoost, and LightGBM models, selecting the champion based on lowest validation RMSE.
5. Defensible Evaluation Metrics:
   - In `metrics()`, compute $R^2$, MAE, RMSE, and add:
     - Mean prediction bias: $\frac{1}{N}\sum (\hat{y}_i - y_i)$
     - Residual distribution statistics: mean, standard deviation, skewness
     - Spatial error autocorrelation: compute Moran's I on spatial residuals to verify that prediction errors are spatially random rather than clustered.
6. Genuine TreeSHAP / SHAP Explainability:
   - Verify exact additive TreeSHAP explainability down to $|base + \sum shap - y_{pred}| < 10^{-4}$.
   - Provide global feature importance, zone-specific base values, and contributions in understandable terms.
   - Enforce non-causal attribution language in returned explanations (clarify statistical associations vs causal interventions).
7. Verification:
   - Run `pytest backend/tests/test_ml_xai.py`. Ensure all tests pass.
   - Document all changes and test outputs in `handoff.md`.

Write your report to `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent3_ml_xai\handoff.md` and send a message when complete.
