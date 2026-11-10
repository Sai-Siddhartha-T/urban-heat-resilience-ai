# Handoff Report: Milestone M3 — Defensible Machine Learning, Climate Analytics & Spatial XAI

**Author**: AGENT 3 (`agent3_ml_xai` / Machine Learning & Spatial XAI Engineer)  
**Recipient**: Orchestrator (`ef9393af-13d2-4069-906d-ff502c4a45d2`)  
**Date**: 2026-11-10  
**Handoff Type**: Hard (Milestone M3 Tasks Complete)  
**State Folder**: `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent3_ml_xai`  

---

## 1. Observation

1. **Target Variable Definition & Service Redundancy**:
   - Prior to upgrade, target handling was implicitly anchored to `observed_suhii` with `ml.py` and `ml_train.py` maintaining ~90% duplicate code across `train()`, `evaluate_models()`, and spatial partitioning.
   - Prediction targets were not explicitly typed with scientific descriptions distinguishing Land Surface Temperature (radiometric skin temperature in °C from Landsat TIRS Band 10) from Surface Urban Heat Island Intensity (SUHII in °C relative to rural reference) and 2m ambient air temperature (atmospheric fluid temperature).
   - In `backend/app/services/features.py:22-120`, `TARGET_COLUMNS` lacked `observed_lst`, and no formal target definition schema or differentiation explanation existed.

2. **Temporal Cross-Validation & Anti-Leakage**:
   - `backend/app/services/features.py` implemented `validate_no_leakage()` and 6-block spatial partitioning, but contained no temporal cross-validation utilities to prevent future-to-past temporal leakage across multi-date acquisitions or seasonal periods.
   - `prepare_feature_tensors()` in `backend/app/services/features.py:514-559` enforced train-only median imputation via `fit_imputer=True` exclusively on the training partition, but only extracted `observed_suhii`.

3. **Defensible Evaluation Metrics & Spatial Error Autocorrelation**:
   - In `backend/app/services/ml.py:71-79`, `metrics(y, p)` computed only `{"r2": ..., "rmse": ..., "mae": ...}`.
   - Mean prediction bias ($\frac{1}{N}\sum (\hat{y}_i - y_i)$), residual distribution statistics (residual mean, standard deviation, and Fisher-Pearson skewness), and spatial error autocorrelation maps via Moran's I on residuals were absent.

4. **TreeSHAP Explainability & Non-Causal Framing**:
   - `backend/app/services/xai.py:217-233` checked TreeSHAP additivity ($|base + \sum shap - pred| < 10^{-4}$), but `compare_zones_xai` used potentially causal language (`"primarily because of"`), and explanation payloads did not provide structured human-understandable narratives with non-causal disclaimers.

5. **Test Execution Evidence**:
   - Executing `pytest backend/tests/test_ml_xai.py` on the upgraded code produced:
     ```
     54 passed, 14 warnings in 51.27s (100% passing)
     ```
   - Executing `pytest backend/tests/test_ml_pipeline.py -k "not test_api"` confirmed zero regressions in pipeline tests:
     ```
     9 passed, 2 deselected, 15 warnings in 28.66s
     ```

---

## 2. Logic Chain

1. **Target Variable Disambiguation (Addressing Observation 1)**:
   - Urban thermal remote sensing distinguishes between:
     - **Land Surface Temperature (LST in °C)**: The thermodynamic skin temperature of surfaces (asphalt, concrete, vegetation, roofs) measured via thermal infrared sensor radiance (Landsat 8/9 TIRS Band 10 / MODIS MOD11A1).
     - **Surface Urban Heat Island Intensity (SUHII in °C)**: The temperature difference relative to a synchronous rural baseline ($SUHII = LST_{\text{urban}} - LST_{\text{rural\_reference}}$).
     - **Ambient Air Temperature ($T_{\text{air}}$ in °C)**: Kinetic atmospheric temperature at 2m height inside a radiation shield. In Heatwise, air temperature is strictly an input meteorological predictor, never the satellite target.
   - In `features.py`, introduced `PredictionTarget` enum (`SUHII = "suhii"`, `LST = "lst"`), `TARGET_DEFINITIONS` dictionary with physical definitions, formulas, and sensor sources, `get_target_definition()`, and `explain_target_differentiation()`.
   - Updated `extract_feature_frame()` and `prepare_feature_tensors()` to resolve both `suhii` and `lst` targets.

2. **Spatial & Temporal Cross-Validation Pipeline (Addressing Observation 2)**:
   - To prevent future-to-past temporal leakage across multi-date acquisitions, created `TemporalFold`, `TemporalSplitResult`, and `temporal_split()` in `features.py`.
   - `temporal_split()` sorts observations chronologically and generates forward-chaining expanding window partitions where $\max(\text{train\_timestamps}) \le \min(\text{val\_timestamps})$.
   - In `ml.py`, consolidated `train()` to support `validation_strategy: Literal["spatial", "temporal"] = "spatial"` and `target: Union[PredictionTarget, str] = "suhii"`.
   - Enforced train-only `SimpleImputer(strategy="median")` fitting, applying out-of-sample transforms to validation and test folds without leakage.

3. **Defensible Evaluation Metrics & Moran's I on Residuals (Addressing Observation 3)**:
   - Upgraded `metrics()` in `ml.py` to calculate:
     - $R^2$ (`r2_score`), RMSE (`sqrt(mean_squared_error)`), MAE (`mean_absolute_error`)
     - Mean prediction bias: $\frac{1}{N}\sum (\hat{y}_i - y_i)$ (`bias` and `mean_prediction_bias`)
     - Residual distribution stats: `residual_mean`, `residual_std`, `residual_skewness` (Fisher-Pearson coefficient using `scipy.stats.skew`)
     - Moran's I spatial error autocorrelation on residuals via `calculate_spatial_morans_i()` using inverse distance spatial weights $w_{ij} = \frac{1}{d(i, j) + \epsilon}$ ($w_{ii} = 0$), theoretical expected value $E[I] = -\frac{1}{N-1}$, analytical randomization variance, standard normal z-scores, and two-tailed p-values.
     - Added `generate_spatial_error_map()` producing zone-level residuals, absolute errors, and standardized z-scores.

4. **Tournament & Additive TreeSHAP with Non-Causal Framing (Addressing Observation 4)**:
   - Maintained competitive tournament across Random Forest, XGBoost, and LightGBM selecting the champion strictly by lowest validation RMSE.
   - Preserved exact TreeSHAP additivity verification down to $|base + \sum shap - pred| < 10^{-4}$.
   - Added `NON_CAUSAL_DISCLAIMER`, `FEATURE_HUMAN_NAMES`, and `format_understandable_contributions()` in `xai.py`.
   - Updated `explain_zone()`, `compare_zones_xai()`, and `get_spatial_shap_contributions()` to return explicit `"attribution_type": "statistical_association"`, non-causal disclaimers, and human-readable narratives to prevent users from conflating statistical correlations with causal intervention cooling.

5. **Test Verification (Addressing Observation 5)**:
   - Expanded `backend/tests/test_ml_xai.py` with 15 new test methods (54 total) covering all requirements. All 54 tests pass cleanly.

---

## 3. Caveats

- Live satellite model inference relies on either ingested Landsat raster zonal averages or demonstration benchmarks; when raster values have cloud contamination or missing bands, the median imputer fitted on training data handles missing values cleanly.
- Moran's I spatial residual autocorrelation requires at least 4 geographical zones with non-identical centroids; when $N < 4$, `calculate_spatial_morans_i` gracefully returns an `insufficient_data` indicator.

---

## 4. Conclusion

Milestone M3 is complete. The Heatwise machine learning and spatial XAI pipeline now provides:
1. Scientifically defensible target variable definitions (`PredictionTarget.SUHII` and `PredictionTarget.LST`) strictly differentiated from 2m ambient air temperature.
2. Strict anti-leakage feature pipeline with train-only `SimpleImputer` fitting.
3. Dual spatial (6-block with isolated buffer fold and KMeans) and temporal (forward-chaining expanding window) cross-validation preventing spatial and temporal leakage.
4. Competitive model tournament (Random Forest, XGBoost, LightGBM) selecting champion by validation RMSE.
5. Defensible evaluation metrics including Mean Prediction Bias, residual distribution statistics, and Moran's I spatial error autocorrelation on residuals.
6. Exact additive TreeSHAP explainability down to $|base + \sum shap - pred| < 10^{-4}$ with understandable contributions and strict non-causal attribution language.

---

## 5. Verification Method

To independently verify this milestone:

1. **Run Full ML & Spatial XAI Test Suite**:
   ```powershell
   pytest backend/tests/test_ml_xai.py
   ```
   *Expected result*: 54 passed in ~50-60s.

2. **Run ML Pipeline Unit Tests**:
   ```powershell
   pytest backend/tests/test_ml_pipeline.py -k "not test_api"
   ```
   *Expected result*: 9 passed, 2 deselected.

3. **Verify Target Definitions & Moran's I Calculation**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'backend'); from app.services.features import TARGET_DEFINITIONS; from app.services.ml import calculate_spatial_morans_i; print('Targets:', list(TARGET_DEFINITIONS.keys())); print('Morans:', calculate_spatial_morans_i([[0,0],[0,1],[1,0],[1,1]], [1,1,-1,-1])['interpretation'])"
   ```
   *Expected result*: Targets include `['suhii', 'lst', 'air_temperature']` and Moran's interpretation is `spatially_clustered`.
