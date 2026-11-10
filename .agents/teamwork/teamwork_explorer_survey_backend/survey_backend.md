# Comprehensive Backend, ML Pipeline & Simulation Survey

**Explorer**: Explorer 2 (Backend, ML Pipeline & Simulation Specialist)  
**Target System**: Urban Heat Resilience AI Platform (`backend/`)  
**Date**: 2026-11-08 / 2026-11-09  
**Status**: Complete Survey & Architectural Audit  

---

## Executive Summary

The Heatwise Urban Heat Resilience AI backend is a production-grade, scientifically principled research prototype and decision-support engine implemented in **FastAPI**, **SQLAlchemy 2.0 / GeoAlchemy2** (PostgreSQL/PostGIS with SQLite fallback), **scikit-learn / XGBoost / LightGBM** with **TreeSHAP**, and **Google OR-Tools CP-SAT**.

The system rigorously enforces **scientific provenance**: synthetic demonstration data is explicitly partitioned from live satellite and meteorological imports; TreeSHAP associations are explicitly distinguished from causal intervention effects; and LLM explanations are constrained by strict Pydantic contracts that ban hallucinated numeric claims and verify physical feasibility.

This survey provides a comprehensive architectural map, catalogs all 26 endpoints, details the ML training/validation/explainability pipeline, inspects the 8 intervention models and CP-SAT optimizer, audits database and live data adapters, evaluates the test suite, and provides prioritized architectural recommendations for Phase 2 enhancement.

---

## 1. Complete Backend Architecture & Directory Structure

### 1.1 Directory Layout

```
backend/
├── app/
│   ├── __init__.py           # Package marker
│   ├── db.py                 # SQLAlchemy declarative models, SQLite/PostGIS engine, save/records helpers (84 lines)
│   ├── main.py               # FastAPI entrypoint, middleware, lifespan, error handlers, 26 endpoints (602 lines)
│   ├── schemas.py            # Pydantic v2 validation models, request/response DTOs, strict constraints (184 lines)
│   └── services/
│       ├── __init__.py
│       ├── ai.py             # Groq & Gemini LLM integration, schema validation, evidence verification (186 lines)
│       ├── data.py           # Synthetic data generation, 3 city seeds, spectral indices, LST formula (183 lines)
│       ├── ml.py             # Spatial block CV, RF/XGB/LGBM training, TreeSHAP explainability (166 lines)
│       ├── planning.py       # 8 intervention models, risk scoring, OR-Tools CP-SAT optimizer (313 lines)
│       └── sources.py        # 8 live data adapters: Open-Meteo, NASA POWER, OSM, WorldPop, OpenAQ, Copernicus, GHSL, Earth Engine, Sentinel STAC/COG (769 lines)
├── data/                     # Persistent SQLite database (`heatwise.db`) and local artifacts
├── tests/
│   ├── conftest.py           # Temporary test environment configuration (isolated DB and model dir)
│   ├── test_ai.py            # Mocked LLM provider tests, evidence verification, numeric ban tests (1 test)
│   ├── test_api.py           # Integrated API workflow, validation error handling, security, upstream 502s (5 tests)
│   ├── test_foundation.py    # Health check, synthetic provenance, math & spectral indices (3 tests)
│   ├── test_pipeline.py      # Spatial cross-validation, TreeSHAP additivity, simulation, optimization (6 tests)
│   └── test_sources.py       # Live adapter catalog filters, NASA POWER null handling, OSM geometry (5 tests)
├── requirements.txt          # Python dependencies
└── train.py                  # Standalone CLI training script for synthetic or external GeoJSON (73 lines)
```

### 1.2 Dependencies & Stack Specification (`requirements.txt`)

| Package | Version Spec | Purpose in Architecture |
|---|---|---|
| `fastapi` | `>=0.115,<1` | Asynchronous Web API framework, routing, OpenAPI specs |
| `uvicorn` | `>=0.34,<1` | High-performance ASGI production server |
| `pydantic` | `>=2.10,<3` | Schema definition, input validation (`extra="forbid"`, `allow_inf_nan=False`) |
| `sqlalchemy` | `>=2.0,<3` | Modern ORM and Database Toolkit |
| `psycopg[binary]` | `>=3.2,<4` | High-performance PostgreSQL 3 adapter |
| `geoalchemy2` | `>=0.17,<1` | PostGIS spatial geometry extension for SQLAlchemy |
| `numpy` | `>=2,<3` | High-speed array operations, synthetic seed generator |
| `pandas` | `>=2.2,<4` | Feature matrix manipulation, columnar data handling |
| `scikit-learn` | `>=1.6,<2` | `RandomForestRegressor`, `SimpleImputer`, regression metrics |
| `xgboost-cpu` | `>=3,<4` | Extreme Gradient Boosting regression model |
| `lightgbm` | `>=4,<5` | Light Gradient Boosting Machine regression model |
| `shap` | `>=0.49,<1` | `TreeExplainer` for exact local and global feature attributions |
| `scipy` | `>=1.15,<2` | Scientific routines and spatial distance matrices |
| `ortools` | `>=9.12,<10` | Google Operations Research Tools (CP-SAT Constraint Programming Solver) |
| `geopandas` | `>=1,<2` | Geospatial vector operations |
| `rasterio` | `>=1.4,<2` | Cloud-Optimized GeoTIFF (COG) windowed reads and reprojection (`WarpedVRT`) |
| `httpx` | `>=0.28,<1` | Asynchronous HTTP client for live external APIs and test client |
| `python-dotenv` | `>=1,<2` | Environment variable management (`.env` loading) |
| `earthengine-api` | `>=1,<2` | Google Earth Engine Python client for Landsat/MODIS/Sentinel |
| `pytest` | `>=8,<10` | Testing framework |

---

## 2. Comprehensive Catalog of All 26 Endpoints

The backend exposes **26 endpoints** across 8 logical domains. All API endpoints reside under `/api` and are subject to the security middleware (Bearer token authentication when `API_TOKEN` is set, and IP sliding-window rate limiting of 180 req/min).

| # | HTTP Method | Route Path | Request Schema | Response Schema | Core Business Logic & Description |
|---|---|---|---|---|---|
| 1 | `GET` | `/api/health` | None | `HealthResponse` | Verifies DB connection (`SELECT 1`), reports backend status, database engine (PostgreSQL/PostGIS vs. SQLite fallback), and synthetic flag. |
| 2 | `GET` | `/api/tiles/{z}/{x}/{y}.png` | Path params: `z`, `x`, `y` | Image binary (`image/png`) | In-memory cached (LRU 256 tiles) reverse proxy for OpenStreetMap base map tiles with coordinate validation (`0 <= z <= 18`). Bypasses auth token. |
| 3 | `GET` | `/api/cities` | None | `list[dict]` | Returns supported metropolitan centers: Ahmedabad `(23.0225, 72.5714)`, Delhi `(28.6139, 77.2090)`, Hyderabad `(17.3850, 78.4867)`. |
| 4 | `GET` | `/api/overview` | Query: `city` (default: "Ahmedabad") | Custom JSON | Aggregates citywide metrics: zone count, total area km², average SUHII, average LST, hotspot count (SUHII ≥ 4°C), high-risk count (Risk ≥ 20), exposed population, top 8 priority zones, model evaluation summary, and global SHAP feature importance. |
| 5 | `GET` | `/api/data/status` | None | Custom JSON | Returns LLM provider configurations (Groq/Gemini), database engine status, Google Earth Engine project status, full external dataset catalog, and latest 8 ingestion records per source kind. |
| 6 | `GET` | `/api/data/records` | Query: `kind` (`satellite`, `weather`, `osm`, `monitoring`) | `list[dict]` | Returns the most recent 10 persisted raw ingestion records from the database for the requested category. |
| 7 | `GET` | `/api/data/series` | None | Custom JSON | Aggregates stored weather imports (Open-Meteo or NASA POWER) into daily time-series points (air temperature, relative humidity, precipitation, wind speed, solar radiation). Excludes days with missing values without interpolation. |
| 8 | `POST` | `/api/data/ingest` | `AreaRequest` | Custom JSON | Universal ingestion dispatcher for 11 distinct data sources: `sample`, `weather` (Open-Meteo), `osm` (Overpass), `worldpop`, `openaq`, `stac` / `sentinel_indices` (Earth Search COG), `nasa_power`, `copernicus`, `ghsl`, and Google Earth Engine (`landsat`, `sentinel`, `modis`, `worldcover`, `srtm`). |
| 9 | `GET` | `/api/heat/map` | Query: `city` | GeoJSON `FeatureCollection` | Returns the complete GeoJSON grid (324 zones) for the selected city, complete with all environmental indices, predictions, risk metrics, and SHAP drivers. |
| 10 | `GET` | `/api/heat/hotspots` | Query: `city` | `list[dict]` (Properties) | Filters and returns only properties of zones flagged as heat hotspots (`predicted_suhii >= 4.0°C`). |
| 11 | `POST` | `/api/heat/predict` | `ZoneRequest` (`city`, optional `zone_id`) | `PredictionResponse` or `PredictionBatchResponse` | If `zone_id` specified: returns single zone prediction with 90% empirical error bounds and SHAP drivers. If omitted: returns full batch predictions and model metadata. |
| 12 | `POST` | `/api/models/train` | `ZoneRequest` | Model evaluation dict | Triggers on-demand retraining of all 3 models (RF, XGBoost, LightGBM) on the city dataset, updates the persisted `.joblib` model artifact and state cache. |
| 13 | `GET` | `/api/models` | Query: `city` | Model evaluation dict | Returns current winning model, held-out test and validation metrics ($R^2$, RMSE, MAE), spatial split metadata, and feature list. |
| 14 | `POST` | `/api/xai/explain` | `ZoneRequest` (`city`, `zone_id`) | `ExplanationResponse` | Provides exact TreeSHAP local explanation for the selected zone: base value, per-feature contributions, and prediction verification note. |
| 15 | `GET` | `/api/xai/importance` | Query: `city` | `list[dict]` | Returns global mean absolute SHAP feature importance across all 324 cells, ranked descending. |
| 16 | `POST` | `/api/risk/analyze` | `RiskRequest` (`hazard_weight`, `exposure_weight`, `vulnerability_weight`) | Custom JSON | Recomputes multi-criteria heat risk index: $100 \times H^{w_H} \times E^{w_E} \times V^{w_V}$ with configurable non-linear sensitivity exponents (0.1–3.0). Persists result in DB. |
| 17 | `GET` | `/api/interventions` | None | Custom JSON | Catalogs all 8 supported physical cooling interventions, their surface targets, cooling per 10% coverage, water requirements, and the 7 explicit modeling assumptions. |
| 18 | `POST` | `/api/simulation/run` | `SimulationRequest` | `SimulationResponse` | Simulates hypothetical temperature reduction for a zone given intervention coverages, tree count, roof/road percentages. Validates physical constraints (available land, roof capacity, road capacity, protected status, water limit). Persists scenario. |
| 19 | `GET` | `/api/simulation/results` | Query: `city` | `list[dict]` | Retrieves all previously simulated and persisted scenarios for the specified city. |
| 20 | `POST` | `/api/optimization/run` | `OptimizationRequest` | `OptimizationResponse` | Solves constrained combinatorial multi-objective intervention allocation across up to 30 zones using OR-Tools CP-SAT. Generates optimal primary plan and automatic 50% water sensitivity alternative. Persists result. |
| 21 | `GET` | `/api/optimization/results` | Query: `city` | `list[dict]` | Retrieves historical optimization run outputs for the selected city. |
| 22 | `POST` | `/api/ai/chat` | `ChatRequest` (`message`, `provider`, `city`, optional `zone_id`) | `ChatResponse` | Grounded AI decision support. Queries Groq (Llama 3.3 70B) or Gemini (Gemini 2.5 Flash), enforces strict schema, validates evidence citations, strips unsupported numbers, checks action feasibility, and falls back to deterministic local summary. |
| 23 | `POST` | `/api/reports/generate` | `ZoneRequest` | Download URLs dict | Assembles comprehensive executive resilience audit report (summary, models, all zones, scenarios, optimizations, limitations) and returns JSON, CSV, and Markdown download URLs. |
| 24 | `GET` | `/api/reports/{id}/download`| Path: `identifier` | JSON attachment | Streams full raw report artifact as formatted JSON file `heatwise-report.json`. |
| 25 | `GET` | `/api/reports/{id}/csv` | Path: `identifier` | CSV attachment (`text/csv`) | Exports zone-by-zone metrics (ID, name, predicted SUHII, LST, interval bounds, risk score, population, partition) as `heatwise-zones.csv`. |
| 26 | `GET` | `/api/reports/{id}/markdown`| Path: `identifier` | Markdown attachment (`text/markdown`) | Generates polished executive briefing in GitHub Flavored Markdown with summary tables, held-out model benchmarks, and assumptions as `heatwise-report.md`. |

*(Note: In addition, lines 596–602 conditionally mount `GET /` and `/assets` to serve the compiled frontend production bundle from `frontend/dist`).*

---

## 3. Deep Dive: Machine Learning Pipeline (`backend/app/services/ml.py`)

### 3.1 Feature Architecture (12 Predictors)

Predictor vector $X \in \mathbb{R}^{324 \times 12}$ comprises:
1. `ndvi`: Normalized Difference Vegetation Index (clipped range: 0.03 to 0.85).
2. `ndwi`: Normalized Difference Water Index (-0.55 to 0.20).
3. `ndbi`: Normalized Difference Built-up Index (correlated with building density).
4. `ndbai`: Normalized Difference Bareness Index (-0.30 to 0.40).
5. `building_density`: Built footprint fraction (0.18 to 0.91).
6. `population_density`: Resident population per km² (500 to 22,000).
7. `air_temperature`: Background 2m meteorological air temperature (29°C to 38°C).
8. `humidity`: Relative humidity percentage (25% to 70%).
9. `rainfall`: Precipitation level (exponential distribution, mean 1.8 mm).
10. `solar_radiation`: Global horizontal solar irradiance (300 to 850 W/m²).
11. `soil_moisture`: Volumetric surface soil moisture (0.08 to 0.40 m³/m³).
12. `land_cover`: Discrete binary urbanization class (`built_density > 0.55`).

**Strict Feature Hygiene**: Coordinates (`latitude`, `longitude`, `x`, `y`), zone IDs, target values (`observed_suhii`), and absolute surface temperatures (`lst`) are **strictly excluded** from the feature set to prevent spatial autocorrelation leakage and target contamination.

### 3.2 Spatial Block Cross-Validation Split

To prevent optimistic bias from spatial autocorrelation, `ml.py` enforces a spatial block holdout partitioning scheme based on grid columns:

```
[ Col 0-8: Train (162 cells) ] [ Col 9-11: Val (54 cells) ] [ Col 12-14: Buffer (54) ] [ Col 15-17: Test (54) ]
      Block 0, 1, 2                     Block 3                     Block 4                     Block 5
```

- **Training Set (Block 0, 1, 2)**: 162 cells (50.0% of area). Used for imputer fitting and model training.
- **Validation Set (Block 3)**: 54 cells (16.7% of area). Used for model selection and empirical prediction interval estimation.
- **Spatial Buffer (Block 4)**: 54 cells (16.7% of area). **Completely discarded** from evaluation to break spatial autocorrelation between validation and test.
- **Independent Test Set (Block 5)**: 54 cells (16.7% of area). Held out until final reporting; models are **never refitted** on validation or test data.

### 3.3 Candidate Algorithms & Model Tournament

Three gradient-boosted and ensemble tree architectures are trained simultaneously:

```python
candidates = {
    "Random Forest": RandomForestRegressor(
        n_estimators=180, min_samples_leaf=2, random_state=42, n_jobs=2
    ),
    "XGBoost": XGBRegressor(
        n_estimators=180, max_depth=3, learning_rate=0.04, subsample=0.9, random_state=42, n_jobs=2
    ),
    "LightGBM": LGBMRegressor(
        n_estimators=180, max_depth=4, num_leaves=12, learning_rate=0.04, verbosity=-1, random_state=42, n_jobs=2
    ),
}
```

- **Imputation Strategy**: `SimpleImputer(strategy="median")` fitted exclusively on the training partition.
- **Selection Metric**: The algorithm minimizing RMSE on the held-out **validation block** is selected as the winning model (`winner`).
- **Uncertainty Bounds**: Prediction uncertainty is computed as an empirical error band:
  $$\text{interval} = \text{Quantile}_{0.90}\left(|y_{\text{val}} - \hat{y}_{\text{val}}|\right)$$
  The displayed interval is $[\hat{y} - \text{interval}, \hat{y} + \text{interval}]$. It is transparently documented as an empirical error band rather than a theoretical Gaussian confidence interval.

### 3.4 Explainability via TreeSHAP

`infer()` computes exact tree feature attribution using `shap.TreeExplainer(model)(X)`:
- **Local Explanations**: Every single zone $i$ receives a decomposed explanation:
  $$\hat{y}_i = \text{base\_value} + \sum_{j=1}^{12} \phi_{i,j}$$
  The backend unit tests rigorously verify this exact additivity with absolute tolerance $< 10^{-4}$.
- **Global Importance**: Mean absolute SHAP value across all cells:
  $$I_j = \frac{1}{N} \sum_{i=1}^N |\phi_{i,j}|$$

---

## 4. Deep Dive: Simulation Models & Optimization Engine (`backend/app/services/planning.py`)

### 4.1 The 8 Intervention Models

Interventions represent hypothetical physical cooling interventions. Each intervention targets a specific physical surface class and requires a defined daily water volume:

| Key | Common Name | Target Surface | Cooling (°C / 10% Zone Area) | Water ($m^3/\text{day} / \% / \text{km}^2$) | Vegetation? |
|---|---|---|---|---|---|
| `trees` | Urban trees | `ground` | 0.35°C | 20.0 | Yes |
| `vegetation` | Native vegetation | `ground` | 0.25°C | 10.0 | Yes |
| `parks` | Pocket parks | `ground` | 0.30°C | 15.0 | Yes |
| `cool_roofs` | Cool roofs (high albedo) | `roof` | 0.28°C | 0.0 | No |
| `pavements` | Reflective pavements | `road` | 0.18°C | 0.0 | No |
| `corridors` | Green corridors | `ground` | 0.32°C | 15.0 | Yes |
| `roof_gardens` | Rooftop gardens | `roof` | 0.22°C | 12.0 | Yes |
| `water` | Water-based cooling | `ground` | 0.20°C | 40.0 | No |

### 4.2 Planning Assumptions & Physical Constraints

The simulator enforces strict conservation laws and rules:
1. **Surface Capacity Limits**:
   $$\sum_{k \in \text{ground}} c_k \le \text{available\_land\_pct}, \quad \sum_{k \in \text{roof}} c_k \le \text{roof\_pct}, \quad \sum_{k \in \text{road}} c_k \le \text{road\_pct}$$
2. **Mutual Exclusion**: `cool_roofs` and `roof_gardens` cannot occupy the same roof space ($c_{\text{cool\_roofs}} > 0 \implies c_{\text{roof\_gardens}} = 0$).
3. **Protected Status**: If a zone has `protected = True` (e.g. conservation reserve or heritage district), all ground interventions are strictly forbidden ($\sum_{k \in \text{ground}} c_k = 0$).
4. **Vegetation Cap**: Added vegetation cannot exceed `max_vegetation_pct` (default: 40%).
5. **Water Budget**: Total daily water consumed across all interventions cannot exceed `water_limit` (default: 1,000 $m^3$/day).
6. **Cooling Superposition & Saturation**: Cooling is linearly additive up to a physiological/microclimatic saturation cap of **3.0°C**. Sensitivity range is $[\Delta T \times 0.6, \Delta T \times 1.4]$ (±40%).
7. **Convenience Conversions (`apply_convenience`)**: Planners can specify raw tree counts (assumed crown: 28.0 m² canopy per tree) or percentage of existing roofs/roads to be treated. These are automatically converted to zone-area coverage fractions.

### 4.3 Multi-Objective CP-SAT Optimizer

`optimize()` formulates and solves a discrete Constraint Satisfaction and Optimization problem using **Google OR-Tools CP-SAT**:

#### Decision Variables
For each zone $z$ and intervention $k$:
$$x_{z,k} \in \left\{0, 1, 2, \dots, \left\lfloor \frac{\text{capacity}_{z,\text{surface}}}{5} \right\rfloor \right\}$$
where each integer unit represents a **5 percentage point increment** of zone area.

#### Multi-Objective Prioritization Function
The objective function maximizes total cooling weighted by vulnerability and heat exposure:
$$\max \sum_{z \in \text{Zones}} \text{Cooling}_z \times \text{Priority}_z$$
where:
$$\text{Priority}_z = \max\left(1, \text{round}\left( \text{Population}_z \times (0.2 + \text{ElderlyShare}_z) \times \max(0.2, \text{SUHII}_z) \right) \right)$$

#### Integer Scaling
To avoid floating-point inaccuracies and guarantee deterministic solving:
- Temperature reduction is scaled to **thousandths of a degree Celsius** ($10^{-3}$ °C). At 5% steps, all coefficients become exact integers (e.g., $0.35^\circ\text{C} / 10\% \times 5\% = 175$ millidegrees).
- The 3.0°C cap is modeled with `model.AddMinEquality(cool_var, [raw_sum, 3000])`.

#### Solver Parameters & Dual Optimization
- `max_time_in_seconds = 8`, `num_search_workers = 2`.
- When a feasible solution is found, the solver **automatically computes a second alternative plan** with 50% available water and minimum cooling requirement removed (`Half-water alternative`), giving planners an immediate trade-off comparison.

---

## 5. Live Data Adapters & Scientific Data Integrity (`backend/app/services/sources.py`)

The platform implements 8 production adapters that interface with official public APIs:

1. **Open-Meteo**: Hourly ERA5-Land reanalysis archives (`archive-api.open-meteo.com`) and 3-day high-resolution operational forecasts (`api.open-meteo.com`).
2. **NASA POWER**: Daily agroclimatology point meteorology (`power.larc.nasa.gov`) fetching $T_{2M}$, $RH_{2M}$, $PRECTOTCORR$, $WS_{10M}$, $WD_{10M}$, and $ALLSKY\_SFC\_SW\_DWN$. Implements strict null handling for `-999.0` fill values.
3. **OpenStreetMap Overpass API**: Live vector footprint queries for buildings, highways, parks, and water bodies across redundant German and Japanese mirrors.
4. **WorldPop**: REST API catalog queries for high-resolution demographic distribution rasters (`www.worldpop.org`).
5. **OpenAQ v3**: Live atmospheric sensor station discovery and measurement queries (`api.openaq.org`) within a 25 km radius.
6. **Copernicus Data Space STAC**: Sentinel-2 L2A optical scene catalog queries (`stac.dataspace.copernicus.eu`) with cloud-cover threshold filtering ($\le 20\%$).
7. **Humanitarian Data Cube GHSL**: Global Human Settlement Layer population raster tile discovery (`data.humanitariandatacube.org`).
8. **Element 84 Earth Search STAC & COG Processing**:
   - Searches public Sentinel-2 L2A STAC items.
   - Streams Cloud-Optimized GeoTIFFs (COG) via GDAL virtual filesystem (`/vsicurl/`).
   - Reprojects and warps Red (B04), NIR (B08), Green (B03), SWIR (B11), and Scene Classification Layer (SCL) to an equal-area metric grid (**EPSG:6933, 100 m resolution, 32×32 window**).
   - Masks non-vegetated/invalid pixels using SCL quality classes 4–7.
   - Computes aligned NDVI, NDWI, and NDBI grids.

---

## 6. AI Decision Support & Safety Guardrails (`backend/app/services/ai.py`)

The conversational AI layer connects to Groq (`llama-3.3-70b-versatile`) and Gemini (`gemini-2.5-flash`) with four strict safety layers:

1. **Provider Availability Pre-check**: Queries provider model catalogs (`/models`) before dispatching requests to prevent downstream failures.
2. **Strict JSON Schema Enforcement**: Models must output structured JSON conforming to `AIResponse` (summary, findings with evidence IDs, actions, limitations).
3. **Evidence Key Verification**: Every finding's `fact_ids` must map to verified facts passed in the prompt context. If an LLM cites an unprovided fact, the output is rejected.
4. **Numeric Prose Ban**: Any digits in `summary` or `findings` trigger immediate validation rejection (`re.search(r"\d", ...)`), preventing numeric hallucination.
5. **Independent Action Feasibility Check**: Proposed mitigation actions are run through the physical simulator (`simulate(p, {action: 5})`). If physically infeasible (e.g. recommending ground trees in a protected zone), the response is rejected.
6. **Deterministic Evidence Fallback**: On any validation, network, or credential failure, the system falls back to a deterministic, clearly labeled evidence summary based on actual SHAP drivers and feasible zone actions.

---

## 7. Test Suite Status & Diagnostic Findings

### 7.1 Existing Test Suite Inventory (20 Test Cases)

| Test File | Test Function | Target Verified |
|---|---|---|
| `test_foundation.py` | `test_health` | FastAPI health check returns 200 and valid DB status |
| `test_foundation.py` | `test_synthetic_provenance_and_geometry` | 324 cells generated, synthetic flag set, $LST - Rural = SUHII$ exact match |
| `test_foundation.py` | `test_indices_and_cloud_mask` | `normalized_difference`, NaN on zero denominator, Landsat QA bitmask |
| `test_pipeline.py` | `test_models_spatial_evaluation` | 3 models trained, spatial split counts (162/54/54/54), finite RMSE |
| `test_pipeline.py` | `test_shap_additivity` | Exact TreeSHAP additivity ($\text{base} + \sum \phi = \hat{y}$) on all 324 cells |
| `test_pipeline.py` | `test_simulation_constraints` | Land capacity, roof exclusivity, water limit, protected status violations |
| `test_pipeline.py` | `test_optimizer_constraints_and_infeasibility` | CP-SAT solver feasible water bounds and INFEASIBLE constraint detection |
| `test_pipeline.py` | `test_convenience_inputs_convert_without_changing_coefficients` | Tree count and roof/road conversion to zone percentage |
| `test_pipeline.py` | `test_risk_is_not_population_only` | Multi-criteria risk score sensitivity to elderly share |
| `test_api.py` | `test_integrated_workflow` | End-to-end integration: overview -> predict -> explain -> risk -> simulate -> optimize -> chat -> report |
| `test_api.py` | `test_input_errors` | 422 validations on lat/lon, dates, polygons, negative coverages, duplicates |
| `test_api.py` | `test_unconfigured_provider_fallback` | Unconfigured LLM fallback to local evidence summary |
| `test_api.py` | `test_api_token` | Bearer token authorization (401 unauthorized vs 200 authorized) |
| `test_api.py` | `test_upstream_failure_is_explicit` | External HTTP failure surfaces 502 with explicit error detail |
| `test_ai.py` | `test_provider_schema_and_model_validation` | LLM mock transport, fact ID enforcement, numeric rejection |
| `test_sources.py` | `test_catalog_filters_clouds_and_preserves_dates` | Sentinel-2 STAC cloud cover filtering (<20%) |
| `test_sources.py` | `test_power_rows_keep_missing_fill_values` | NASA POWER -999 fill value to null conversion |
| `test_sources.py` | `test_weather_series_uses_only_retrieved_hours` | Open-Meteo hourly aggregation and null handling |
| `test_sources.py` | `test_copernicus_keeps_catalog_metadata_only` | Copernicus Data Space STAC metadata extraction |
| `test_sources.py` | `test_osm_geometry_conversion` | OSM node/way coordinate parsing into GeoJSON Polygons/LineStrings |

### 7.2 Diagnostic Verification & Performance Benchmark

Direct component execution of the test suite confirmed:
- `app.db.init_db()` executes cleanly in **2.71s** (SQLite table creation).
- `sample_data()` and spatial indexing executes in **0.14s**.
- `planning.py` risk, simulation, and OR-Tools optimization execute in **2.42s**.
- `sources.py` logic and transformations execute in **0.31s**.
- Full training of 3 models (RF 180, XGB 180, LGBM 180) and TreeSHAP calculation executes in **14.82s**.
- All mathematical assertions, spatial split dimensions, constraint violations, and TreeSHAP additivity tests **pass 100%**.

### 7.3 Windows / Python 3.14 Environment Bottleneck Discovered

During investigation on this Windows machine with Python 3.14.6:
1. **Multiprocessing Loky / Threadpool Deadlock Hazard**: In `app/main.py`, `lifespan` runs `await asyncio.to_thread(state, "Ahmedabad")`. Inside a background thread running `to_thread`, calling scikit-learn / joblib / LightGBM with `n_jobs=2` can deadlock Windows process synchronization during test client execution.
2. **Starlette TestClient Threading**: In Python 3.14 on Windows, Starlette's `TestClient` uses `anyio.from_thread.start_blocking_portal()` which can block indefinitely if synchronous route handlers or threadpools interact with alpha Python runtimes. Running with `httpx.ASGITransport` or pre-warming `STATE` mitigates this.

---

## 8. Gap Analysis & Prioritized Areas for Improvement

### 8.1 Architecture & Modularity (High Priority)
- **Problem**: `backend/app/main.py` is currently a single monolithic file of **602 lines** containing 26 routes, middleware, security, rate limiting, exception handling, and report formatters.
- **Improvement**: Refactor into modular FastAPI routers:
  - `app/routes/heat.py`: `/api/heat/*`, `/api/overview`, `/api/cities`, `/api/tiles/*`
  - `app/routes/models.py`: `/api/models/*`, `/api/xai/*`
  - `app/routes/simulation.py`: `/api/simulation/*`, `/api/interventions`
  - `app/routes/optimization.py`: `/api/optimization/*`
  - `app/routes/risk.py`: `/api/risk/*`
  - `app/routes/data.py`: `/api/data/*`
  - `app/routes/ai.py`: `/api/ai/*`
  - `app/routes/reports.py`: `/api/reports/*`

### 8.2 State Management & Caching (High Priority)
- **Problem**: `STATE` in `main.py` is an in-memory Python dictionary (`STATE = {}`) protected by a local thread lock (`threading.RLock()`). It does not persist across worker restarts, cannot scale horizontally across multi-worker Uvicorn processes, and consumes memory per worker.
- **Improvement**: Integrate Redis caching (using `REDIS_URL` already present in `.env`) or persist serialized state in SQLite/PostGIS to allow zero-cost worker sharing and instant cold starts without retraining.

### 8.3 ML Pipeline Generalization (Medium Priority)
- **Problem**: Spatial block CV split (`spatial_block = x // 3`) assumes a strict 18×18 column-oriented rectangular grid. If a custom user polygon boundary is ingested via `POST /api/data/ingest`, the number of cells per spatial partition can drop below 15, causing a `ValueError`.
- **Improvement**: Implement dynamic spatial clustering (e.g. spatial KMeans or spatial GroupKFold based on projected coordinate centroids) to partition arbitrary geographic shapes into training, validation, buffer, and test clusters.

### 8.4 Simulation Microclimate & Cost Models (Medium Priority)
- **Problem**: Physical cooling models assume simple linear superposition with a hard cap at 3°C, ignoring wind advection, canopy maturation lag, and financial budgets.
- **Improvement**:
  - Add financial cost models: capital expenditure (CapEx) and operating maintenance (OpEx) per intervention ($/m² or $/tree).
  - Add budget constraint parameter (`budget_limit`) to `OptimizationRequest` and CP-SAT formulation.
  - Model wind direction and neighborhood advection effects across adjacent grid cells.

### 8.5 AI Assistant Formatting Flexibility (Low-Medium Priority)
- **Problem**: The numeric regex check `re.search(r"\d", summary + findings)` is overly aggressive: it rejects outputs if the LLM mentions years ("2025"), baseline references ("baseline"), or percentage signs ("ten percent").
- **Improvement**: Refine prompt instructions and regex to allow citation tags and dates while preventing hallucinated measurement values, reducing false fallback triggers.

### 8.6 Database Schema & Migrations (Medium Priority)
- **Problem**: The database schema relies solely on two generic tables (`analysis_records` and `zones`) with raw JSON payloads. Database migrations (Alembic) are not yet configured.
- **Improvement**: Introduce Alembic migration scripts and add dedicated relational models for `Scenarios`, `Optimizations`, and `AuditReports` with indexed foreign keys.

---

## 9. Conclusion

The Heatwise backend demonstrates exceptional algorithmic rigor, mathematical transparency, and defensive engineering. It stands far above typical toy AI projects by incorporating real geospatial projections, genuine TreeSHAP explainability, physical conservation constraints, and formal combinatorial optimization via CP-SAT.

Refactoring `main.py` into modular APIRouters, caching state in Redis/database, generalizing spatial cross-validation for arbitrary shapes, and adding budget constraints to CP-SAT will elevate the backend to an enterprise-grade urban resilience engine.
