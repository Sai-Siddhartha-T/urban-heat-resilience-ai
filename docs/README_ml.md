# Machine Learning Pipeline & Explainability (XAI)

This document describes the modular machine learning pipeline, spatial cross-validation methodology, candidate model tournament, and TreeSHAP explainability service in the Urban Heat Resilience AI platform.

---

## 1. Overview & Objectives

Surface Urban Heat Island Intensity (SUHII) varies sharply across complex urban environments due to the spatial configuration of vegetation, water bodies, built density, meteorological factors, and human demographics. Standard random cross-validation yields inflated, over-optimistic accuracy metrics due to spatial autocorrelation between adjacent grid cells.

The Heatwise ML pipeline provides:
1. **Modular Architecture**: Clean separation between feature engineering (`features.py`), spatial cross-validation & training (`ml_train.py`), and TreeSHAP explainability (`xai.py`), unified under `ml.py`.
2. **KMeans Spatial Cross-Validation**: `spatial_split(zones, n_folds)` clusters zone centroids to guarantee that validation and test sets are spatially disjoint from training sets, preventing spatial autocorrelation leakage.
3. **Model Tournament**: Parallel training of three high-capacity ensemble regressors (**Random Forest**, **XGBoost**, **LightGBM**) with automated selection of the best-performing model by validation Root Mean Squared Error (RMSE).
4. **TreeSHAP Explainability**: Generation and persistence of exact TreeSHAP local feature attributions and global feature rankings satisfying the additivity property ($f(x) = \phi_0 + \sum_{i=1}^M \phi_i$).
5. **Real & Synthetic Provenance**: Ingestion of real Landsat/Sentinel satellite indices and WorldPop/Census demographic data, with explicit provenance tracking and synthetic fallback flags.

---

## 2. Architecture & Modules

```
backend/
├── app/
│   ├── services/
│   │   ├── features.py         # Feature extraction, coordinate tensors, spatial_split, anti-leakage checks
│   │   ├── ml_train.py         # Model tournament (RF, XGB, LGBM), validation selection, persistence
│   │   ├── xai.py              # TreeSHAP explainer generation, local attributions, SHAP disk persistence
│   │   ├── ml.py               # Unified facade maintaining 100% backward compatibility
│   │   ├── satellite.py        # Landsat-8, Sentinel-2, MODIS ingestion with synthetic fallbacks
│   │   └── demographics.py     # WorldPop, GHSL, Census ingestion & vulnerability indicators
│   └── routes/
│       ├── heat.py             # Exposes /api/heat/predict (POST & GET, single, batch, ad-hoc)
│       └── models.py           # Exposes /api/xai/shap and /api/models
├── tests/
│   └── test_ml_pipeline.py     # Comprehensive unit tests for modular ML and XAI components
└── train.py                    # Standalone training script with --city, --folds, and --input flags
```

---

## 3. Feature Space & Data Provenance

### 3.1 Feature Catalog

The core feature matrix uses 12 real satellite, environmental, and demographic predictors:

| Feature Name | Category | Description | Typical Range / Units | Source |
|---|---|---|---|---|
| `ndvi` | Optical Satellite | Normalized Difference Vegetation Index | $[-0.2, 0.9]$ | Landsat-8 / Sentinel-2 |
| `ndwi` | Optical Satellite | Normalized Difference Water Index | $[-0.6, 0.4]$ | Landsat-8 / Sentinel-2 |
| `ndbi` | Optical Satellite | Normalized Difference Built-Up Index | $[-0.5, 0.8]$ | Landsat-8 / Sentinel-2 |
| `ndbai` | Thermal Satellite | Normalized Difference Built-Up Area Index | $[-0.4, 0.5]$ | Landsat-8 Thermal |
| `building_density` | Urban Morphology | Impervious built footprint fraction | $[0.0, 1.0]$ | OpenStreetMap / GHSL |
| `population_density` | Demographics | Human population per square kilometer | $[0, 30000]\text{ /km}^2$ | WorldPop / Census |
| `air_temperature` | Environmental | Ambient air temperature | $[20.0, 48.0]\text{ }^\circ\text{C}$ | OpenWeather / NASA POWER |
| `humidity` | Environmental | Relative humidity | $[15.0, 95.0]\text{ }^\circ\text{C}$ | OpenWeather / NASA POWER |
| `rainfall` | Environmental | Precipitation rate | $[0.0, 50.0]\text{ mm/day}$ | NASA POWER / ERA5 |
| `solar_radiation` | Environmental | Downwelling solar irradiance | $[200.0, 1000.0]\text{ W/m}^2$ | NASA POWER |
| `soil_moisture` | Environmental | Volumetric soil water content | $[0.05, 0.55]\text{ m}^3/\text{m}^3$ | NASA POWER / SMAP |
| `land_cover` | Land Classification | Dominant land classification code | Categorical $[0, 1]$ | Dynamic World / WorldCover |

### 3.2 Target Variable Formulation
$$
\text{observed\_suhii} = \text{LST}_{\text{urban}} - \text{LST}_{\text{rural\_reference}}
$$
Where:
- $\text{LST}_{\text{urban}}$: Land surface temperature measured in Celsius (e.g. Landsat Band 10 thermal conversion).
- $\text{LST}_{\text{rural\_reference}}$: Stable regional rural reference temperature in Celsius.

### 3.3 Strict Anti-Data Leakage Safeguards
To prevent target and spatial leakage into predictors:
- **Forbidden Predictor Exclusions**: Target variables (`observed_suhii`, `lst`, `rural_reference`) and geographic identifiers/coordinates (`latitude`, `longitude`, `spatial_block`, `partition`, `id`, `name`) are strictly excluded from the feature matrix via `validate_no_leakage(feature_list)`.
- **Train-Only Imputation**: `SimpleImputer(strategy="median")` is fit **strictly on the training split** (`fit_imputer=True`). The validation, test, and inference sets are transformed using the fitted training imputer without re-estimating statistics.

### 3.4 Data Provenance & Fallback Tracking
The pipeline inspects metadata for `source`, `synthetic`, and `fallback` flags from the upstream satellite and demographic modules:
```python
provenance = check_data_provenance(metadata)
# Returns:
# {
#   "synthetic": bool,
#   "fallback": bool,
#   "satellite_source": str,
#   "demographic_source": str,
#   "provenance_notes": [...]
# }
```

---

## 4. Spatial Cross-Validation Methodology

### 4.1 The Spatial Autocorrelation Problem
Urban cells close to one another exhibit strong spatial autocorrelation (Tobler's First Law of Geography). When adjacent cells are randomly assigned to train and test sets, models can memorize local spatial patterns rather than learning genuine environmental relationships, causing severe generalization failure when deployed on new cities.

### 4.2 Centroid KMeans Partitioning (`spatial_split`)
`spatial_split(zones, n_folds=5, random_state=42)` addresses this by:
1. Extracting centroid coordinates $(x_i, y_i)$ from zone geometries or coordinate properties using `extract_coordinates`.
2. Fitting a `KMeans(n_clusters=n_folds)` model on spatial coordinates.
3. Sorting cluster centroids along the primary spatial variance axis to guarantee geographic continuity.
4. Constructing $K$ distinct folds where validation zones belong to cluster $k$ and training zones belong to all remaining clusters $\{c \neq k\}$.

```python
splits = spatial_split(zones, n_folds=5)

for train_idx, val_idx in splits:
    # train_idx and val_idx are strictly disjoint
    # zones in val_idx share no spatial cluster with train_idx
```

---

## 5. Model Tournament & Selection

### 5.1 Candidate Model Suite
During pipeline training, three high-performance gradient boosted and bagged regressors are trained simultaneously on the training feature tensors:

1. **Random Forest Regressor** (`RandomForestRegressor`):
   - `n_estimators=180`, `min_samples_leaf=2`, `random_state=42`
   - Resilient against feature collinearity and localized noise.
2. **XGBoost Regressor** (`XGBRegressor`):
   - `n_estimators=180`, `max_depth=3`, `learning_rate=0.04`, `subsample=0.9`, `random_state=42`
   - Captures subtle non-linear environmental interactions and threshold effects.
3. **LightGBM Regressor** (`LGBMRegressor`):
   - `n_estimators=180`, `max_depth=4`, `num_leaves=12`, `learning_rate=0.04`, `verbosity=-1`, `random_state=42`
   - Efficient leaf-wise tree growth with fast inference latency.

### 5.2 Selection by Validation RMSE
Model tournament selection is governed strictly by the validation set Root Mean Squared Error (RMSE):
$$
\text{RMSE} = \sqrt{\frac{1}{N_{\text{val}}} \sum_{i=1}^{N_{\text{val}}} (y_i - \hat{y}_i)^2}
$$
The model achieving the minimum validation RMSE is chosen as the winner.

### 5.3 Uncertainty Intervals
A non-parametric 90% confidence interval is computed from validation absolute residual errors:
$$
\text{interval} = \text{Quantile}_{0.90}(|y_{\text{val}} - \hat{y}_{\text{val}}|)
$$
Every prediction is accompanied by `interval_low` ($\hat{y} - \text{interval}$) and `interval_high` ($\hat{y} + \text{interval}$).

---

## 6. Explainable AI (XAI) & TreeSHAP

### 6.1 TreeSHAP Local Attributions
The pipeline computes exact Shapley Additive exPlanations using `shap.TreeExplainer`:
$$
f(x) = \phi_0 + \sum_{j=1}^{M} \phi_j(x)
$$
Where:
- $\phi_0$: The base value (expected SUHII prediction across the background training population).
- $\phi_j(x)$: The local contribution of feature $j$ for zone $x$.
- $f(x)$: The model's predicted SUHII value for that zone.

### 6.2 Global Feature Importance
Global feature importance is ranked by the mean absolute SHAP value across all zones:
$$
I_j = \frac{1}{N} \sum_{i=1}^{N} |\phi_j(x_i)|
$$

### 6.3 Artifact Persistence
All model components and SHAP artifacts are persisted to `models/`:
- `models/{city}.joblib`: Winning model, training imputer, evaluations, and metadata.
- `models/{city}_explainer.joblib`: Serialized `shap.TreeExplainer` instance.
- `models/{city}_shap.joblib`: Persisted SHAP records and global feature rankings for fast API responses.

---

## 7. API Reference

### 7.1 `/api/heat/predict` (POST & GET)

**Predict for single zone:**
```http
POST /api/heat/predict
Content-Type: application/json

{
  "city": "Ahmedabad",
  "zone_id": "ahmedabad-00-00"
}
```
*Response:*
```json
{
  "id": "ahmedabad-00-00",
  "name": "Sector 01 · 01",
  "city": "Ahmedabad",
  "predicted_suhii": 3.42,
  "predicted_lst": 36.42,
  "interval_low": 2.92,
  "interval_high": 3.92,
  "source": "synthetic",
  "shap": {
    "building_density": 1.25,
    "ndvi": -0.84,
    "ndbi": 0.45,
    "soil_moisture": -0.15,
    ...
  }
}
```

**Ad-hoc custom features prediction:**
```http
POST /api/heat/predict
Content-Type: application/json

{
  "city": "Ahmedabad",
  "features": {
    "ndvi": 0.70,
    "ndwi": 0.10,
    "ndbi": -0.20,
    "building_density": 0.25,
    "population_density": 5000,
    "air_temperature": 32.0,
    "humidity": 55.0,
    "rainfall": 3.0,
    "solar_radiation": 500.0,
    "soil_moisture": 0.30,
    "land_cover": 0.0
  }
}
```

### 7.2 `/api/xai/shap` (POST & GET)

**Retrieve local SHAP for specific zone:**
```http
GET /api/xai/shap?city=Ahmedabad&zone_id=ahmedabad-00-00
```
*Response:*
```json
{
  "city": "Ahmedabad",
  "zone_id": "ahmedabad-00-00",
  "prediction": 3.42,
  "base_value": 2.85,
  "shap_values": {
    "ndvi": -0.84,
    "building_density": 1.25,
    ...
  },
  "contributions": { ... },
  "feature_importance": [
    {"feature": "building_density", "importance": 1.05},
    {"feature": "ndvi", "importance": 0.82},
    ...
  ],
  "note": "Actual TreeSHAP feature attributions for zone from persisted model explainer."
}
```

**Retrieve city-wide SHAP records:**
```http
GET /api/xai/shap?city=Ahmedabad
```

---

## 8. Standalone Training CLI

Train the models from the terminal on synthetic baseline or real ingested GeoJSON datasets:

```bash
# Standard spatial cross-validation training on default synthetic city
python backend/train.py --city Ahmedabad

# Explicit KMeans spatial cross-validation with 5 folds
python backend/train.py --city Ahmedabad --folds 5

# Training on external real-world labeled GeoJSON
python backend/train.py --city Ahmedabad --input data/real_ahmedabad_zones.geojson --folds 5
```

---

## 9. Verification & Testing

Execute the comprehensive ML test suite:

```bash
python -m pytest backend/tests/test_ml_pipeline.py -v
```

Verification covers:
- Coordinate extraction across all GeoJSON and tabular formats.
- Disjoint spatial partitions and centroid KMeans clustering.
- Imputer training isolation (guaranteeing no feature distribution leakage).
- Model tournament execution across RF, XGBoost, and LightGBM with selection by validation RMSE.
- Exact TreeSHAP additivity verification on model predictions ($|\phi_0 + \sum \phi_i - \hat{y}| < 10^{-4}$).
- Disk persistence and reloadability of models, explainers, and SHAP records.
- Complete API route validation for `/api/heat/predict` and `/api/xai/shap`.
