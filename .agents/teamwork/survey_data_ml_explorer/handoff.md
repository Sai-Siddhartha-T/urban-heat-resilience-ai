# Comprehensive Survey Report: Scientific, Data Ingestion, ML, Spatial XAI & Optimization Modules

**Working Directory**: `d:\Urban-Heat-Resilience-AI`  
**Author**: Data & ML Pipeline Explorer  
**Milestone**: Survey Phase  
**Date**: 2026-11-09T13:25:00Z  

---

## 1. Observation

### 1.1 Codebase File Topology & Architectural Mapping
Direct examination of `backend/app/services/` and `backend/app/routes/` via directory inspection reveals the current layout:
- **Existing Service Files**:
  - `backend/app/services/sources.py` (769 lines): Ingests external live data from Open-Meteo, NASA POWER, OpenStreetMap Overpass, WorldPop, OpenAQ, Copernicus STAC, GHSL STAC, Google Earth Engine (Landsat, Sentinel-2, MODIS, WorldCover, SRTM), and Element 84 Sentinel-2 COG rasters.
  - `backend/app/services/data.py` (193 lines): Synthetic grid generator (`sample_data`), database dataset persistence (`persist_dataset`), spectral index equations (`spectral_indices`, `normalized_difference`), and Landsat LST conversion (`landsat_lst`).
  - `backend/app/services/ml.py` (338 lines): Spatial partitioning (`assign_spatial_partitions`), model tournament (Random Forest, XGBoost, LightGBM), model persistence / caching (`load_or_train`), spatial inference, and TreeSHAP explainability (`infer`).
  - `backend/app/services/planning.py` (409 lines): Intervention definitions (`INTERVENTIONS`), convenience conversion (`apply_convenience`), IPCC heat-risk index (`risk`), scenario simulation (`simulate`), and Google OR-Tools CP-SAT discrete optimization (`optimize`).
  - `backend/app/services/state.py` (85 lines): Thread-safe in-memory cache and pipeline runner (`analyze`, `state`, `zone`, `get_city_overview`).
  - `backend/app/services/ai.py` (270 lines): LLM orchestrator, numeric guardrails, and Groq/Gemini fallback.
- **Files Not Yet Modularized as Standalone Files in `backend/app/services/`**:
  - `backend/app/services/geospatial.py` (logic currently inside `sources.py` and `data.py`)
  - `backend/app/services/satellite.py` (logic currently inside `sources.py`)
  - `backend/app/services/demographics.py` (catalog logic in `sources.py:worldpop`/`ghsl_catalog`, synthetic demographic properties in `data.py:sample_data`)
  - `backend/app/services/risk.py` (risk logic in `planning.py:risk`, route in `backend/app/routes/risk.py`)
  - `backend/app/services/features.py` (feature definitions in `data.py:FEATURES`)
  - `backend/app/services/xai.py` (SHAP logic in `ml.py:infer`, route in `backend/app/routes/models.py`)
  - `backend/app/services/optimization.py` (CP-SAT optimizer in `planning.py:optimize`, route in `backend/app/routes/optimization.py`)

---

### 1.2 Satellite Data & Earth Observation Findings

#### A. Synthetic vs. Real Data Generation
1. **Synthetic Data (`backend/app/services/data.py:29-143`)**:
   - `sample_data(city, lat, lon, boundary, rural_reference)` generates a 18 × 18 regular grid (up to 324 zones of 1.0 km² each) using deterministic RNG (`np.random.default_rng(42)`).
   - Zone geometry is created as standard WGS84 bounding polygons:
     ```python
     width = 0.009 / math.cos(math.radians(lat))
     height = 0.009
     ```
   - Target surface heat `observed_suhii` is synthetically computed via a linear-noise equation:
     ```python
     suhii = float(
         1.1
         + 4.8 * built
         - 3.2 * ndvi
         - 1.3 * ndwi
         + 1.7 * ndbi
         + 0.075 * (air - 32)
         + 0.001 * solar
         + 0.5 * ndbai
         - 0.8 * moisture
         + rng.normal(0, 0.32)
     )
     ```
   - Metadata explicitly identifies provenance: `"source": "Seeded synthetic demonstration dataset"`, `"synthetic": True`, with explicit disclaimer: `"Synthetic environmental and demographic values; not satellite observations"`.
2. **Real Data Ingestion (`backend/app/services/sources.py`)**:
   - Remote live data calls are strictly real. Line 1: `"Live adapters. Remote errors are never replaced with synthetic responses."`
   - If external APIs fail or are unauthorized, the adapter raises an `httpx.HTTPError` or `ValueError` (propagating HTTP 502/500 to the caller); it never falls back to synthetic mock data.
   - All ingested records are saved to SQLite/PostGIS with `"synthetic": False`.

#### B. Earth Engine Integration (`sources.py:420-498` & `sources.py:662-769`)
- Requires Google Earth Engine credentials and project configuration via `EARTH_ENGINE_PROJECT`.
- Initialized via `ee.Initialize(project=project)`.
- **Landsat 8/9 Collection 2 Level-2 Surface Temperature (LST)** (`sources.py:458-474`):
  - Collections: Merges `LANDSAT/LC08/C02/T1_L2` and `LANDSAT/LC09/C02/T1_L2`.
  - Filters: Bounds to region, date range, and `ee.Filter.eq("PROCESSING_LEVEL", "L2SP")`.
  - Cloud and Radiometric Saturation Masking:
    ```python
    mask = (
        image.select("QA_PIXEL")
        .bitwiseAnd(63)
        .eq(0)
        .And(image.select("QA_RADSAT").eq(0))
    )
    ```
    (Bits 0-5 in `QA_PIXEL` represent fill, dilated cloud, cirrus, cloud, cloud shadow).
  - Landsat LST Conversion (`sources.py:445-451` and `data.py:190-193`):
    ```python
    lst = image.select("ST_B10").multiply(0.00341802).add(149).subtract(273.15).rename("lst")
    ```
    This applies the USGS Collection 2 Level-2 scaling factor and converts Kelvin to Celsius.
  - Surface Reflectance scaling:
    ```python
    sr = image.select(["SR_B3", "SR_B4", "SR_B5", "SR_B6"], ["green", "red", "nir", "swir"]).multiply(0.0000275).add(-0.2)
    ```
- **Sentinel-2 Optical Composite via Earth Engine** (`sources.py:674-704`):
  - Uses `COPERNICUS/S2_SR_HARMONIZED`.
  - Cloud filter: `CLOUDY_PIXEL_PERCENTAGE < 20`.
  - SCL Masking: `scl.gte(4).And(scl.lte(7))` (preserves vegetation, bare soils, water).
  - Band scale: `0.0001`.
  - Median composite calculated across the time window.
- **MODIS MOD11A2 LST** (`sources.py:704-729`):
  - Image collection: `MODIS/061/MOD11A2` (1 km, 8-day composite).
  - Quality mask: `qc = image.select("QC_Day")`, `mask = qc.bitwiseAnd(3).eq(0).And(qc.rightShift(6).bitwiseAnd(3).lte(1))`.
  - LST formula: `image.select("LST_Day_1km").multiply(0.02).subtract(273.15)`.
- **ESA WorldCover & NASA SRTM** (`sources.py:729-744`):
  - `ESA/WorldCover/v200` (10 m, 2021) and `USGS/SRTMGL1_003` (30 m elevation).
- **Sampling & Reprojection in GEE**:
  - Sampled to EPSG:6933 at 1000 m scale: `image.sample(region=region, scale=1000, projection="EPSG:6933", numPixels=500, geometries=True, seed=42)`.

#### C. Sentinel-2 STAC / COG Ingestion & WarpedVRT Windowing (`sources.py:544-659`)
- Public scene discovery queries Element 84 Earth Search: `https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items`.
- Filters scene items where `properties.eo:cloud_cover < 20`.
- COG Reading via `rasterio` and `WarpedVRT` (`sources.py:578-659`):
  - Resolves bounding box from target `lat, lon` and transforms from `EPSG:4326` to `EPSG:6933` using `pyproj.Transformer`.
  - Constructs affine transform for a 32 × 32 grid of 100 m pixels: `from_origin(x - 1600, y + 1600, 100, 100)`.
  - Reads COGs directly from AWS S3 (`https://sentinel-cogs.s3.us-west-2.amazonaws.com/`) with GDAL streaming configuration:
    ```python
    options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "25",
        "GDAL_HTTP_MAX_RETRY": "1",
    }
    ```
  - Bands read: `red`, `nir`, `green`, `swir16`, `scl`.
  - SCL masking: pixels where `scl` is in `[4, 5, 6, 7]` are retained; others masked to `np.nan`.
  - Scaled using STAC `raster:bands` scale (0.0001) and offset (0.0).

#### D. Spectral Indices Implementation (`data.py:168-187`)
- Safe normalized difference avoiding divide-by-zero:
  ```python
  def normalized_difference(a, b):
      a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
      return np.divide(
          a - b,
          a + b,
          out=np.full(np.broadcast_shapes(a.shape, b.shape), np.nan),
          where=np.abs(a + b) > 1e-10,
      )
  ```
- **NDVI**: `(nir - red) / (nir + red)`
- **NDWI**: `(green - nir) / (green + nir)` (McFeeters water index)
- **NDBI**: `(swir - nir) / (swir + nir)` (Built-up index)
- **NDBaI**: `(swir - thermal) / (swir + thermal)` (Bareness index)
  - Caveat explicitly noted in `sources.py:490-494` and `data.py:184-187`: In real satellite data (Landsat/Sentinel), NDBaI is omitted from uncalibrated feeds because reflectance (0-1) and thermal temperature (Celsius) are physically not commensurate without radiometric normalization.

---

### 1.3 Demographic Data & Vulnerability Findings

#### A. Data Sources
- **WorldPop (`sources.py:276-294`)**:
  - Live query to WorldPop REST API catalog: `https://www.worldpop.org/rest/data/pop/wpgp?iso3={country}`.
  - Returns metadata of published population rasters for the country and year (default IND, 2020).
  - Explicit limitation noted: `"Raster download and alignment required before demographic use. Age/sex and socioeconomic data are not inferred."`
- **GHSL GHS-POP (`sources.py:382-417`)**:
  - Live query to Humanitarian Data Cube STAC API: `https://data.humanitariandatacube.org/stac-api/collections/jrc_ghsl_pop/items?bbox={lon-0.05},{lat-0.05},{lon+0.05},{lat+0.05}`.
  - Discovers 100 m / 3 arc-second population raster tiles intersecting the bounding box.
  - Explicit limitation noted: `"Tile catalog only. Population counts were not read from the rasters, and age or sex structure is not included."`
- **Census of India**:
  - Not integrated into live ingestion. In the baseline system, demographic properties (`population`, `population_density`, `elderly_share`) are deterministically simulated in `data.py:sample_data()`.
  - Socioeconomic indicators (`socioeconomic_data`) are explicitly set to `None`.

#### B. Demographic Feature Joining & Heat-Risk Framework
- Currently in `data.py:sample_data()`, demographic attributes are assigned directly to each 1 km² polygon feature:
  - `population`: Uniform random between 500 and 22,000.
  - `population_density`: Equals `population / area_km2` (area = 1.0 km²).
  - `elderly_share`: Uniform random between 0.04 and 0.18 (4% to 18%).
- Heat-Risk index is implemented in `backend/app/services/planning.py:140-163`:
  ```python
  def risk(p, weights=(1, 1, 1)):
      hazard = min(1, max(0, p.get("predicted_suhii", p.get("observed_suhii", 2.0))) / 8)
      exposure = min(1, p["population_density"] / 25000)
      vulnerability = min(1, p["elderly_share"] / 0.25)
      value = (
          100
          * hazard ** weights[0]
          * exposure ** weights[1]
          * vulnerability ** weights[2]
      )
      return {
          "risk_score": value,
          "hazard": hazard,
          "exposure": exposure,
          "vulnerability": vulnerability,
          "risk_level": "High" if value >= 20 else "Moderate" if value >= 8 else "Low",
          "missing_indicators": [
              "Socioeconomic status",
              "Health conditions",
              "Access to cooling",
          ],
          "method": "100 × (SUHII / 8)^wH × (population/km² / 25000)^wE × (elderly share / .25)^wV; components clipped to [0,1]. Synthetic age share is a limited vulnerability proxy.",
      }
  ```
- **Hazard component**: SUHII clipped to [0, 8] °C and scaled to [0, 1].
- **Exposure component**: Population density clipped to [0, 25,000] per km² and scaled to [0, 1].
- **Vulnerability component**: Elderly share clipped to [0, 25%] and scaled to [0, 1].
- **Composite formulation**: Multiplicative formulation `100 * H^wH * E^wE * V^wV`, aligning directly with the IPCC AR5/AR6 risk framework (Hazard × Exposure × Vulnerability).
- Parametric weighting is exposed via `POST /api/risk/analyze`, allowing planners to tune `hazard_weight`, `exposure_weight`, and `vulnerability_weight` in `[0.1, 3.0]`.

---

### 1.4 Machine Learning & Spatial XAI Findings

#### A. Models Implemented (`backend/app/services/ml.py:199-234`)
Three regression models participate in an automated competitive tournament:
1. **Random Forest (`RandomForestRegressor`)**:
   - `n_estimators=180, min_samples_leaf=2, random_state=42`
2. **XGBoost (`XGBRegressor`)**:
   - `n_estimators=180, max_depth=3, learning_rate=0.04, subsample=0.9, random_state=42`
3. **LightGBM (`LGBMRegressor`)**:
   - `n_estimators=180, max_depth=4, num_leaves=12, learning_rate=0.04, verbosity=-1, random_state=42`
- **Tournament Selection**: All three models are fitted on the spatial training set and scored on the spatial validation set. The model achieving the minimum validation RMSE is designated the winner (`winner = min(evaluations, key=lambda m: m["validation"]["rmse"])["model"]`).
- **Concurrency / Speed Tuning**: Parameterized by `ML_JOBS` / `ML_N_JOBS` / `FAST_STARTUP` environment variables.

#### B. Feature Configuration & Strict Anti-Leakage
- Feature list defined in `data.py:FEATURES`:
  ```python
  FEATURES = [
      "ndvi", "ndwi", "ndbi", "ndbai",
      "building_density", "population_density",
      "air_temperature", "humidity", "rainfall",
      "solar_radiation", "soil_moisture", "land_cover"
  ]
  ```
- Missing values are imputed using `SimpleImputer(strategy="median")`, fitted strictly on training data (`imputer.fit_transform(frame.loc[tr, FEATURES])`).
- **Strict Leakage Prevention**:
  - Geographic coordinates (`latitude`, `longitude`, `x`, `y`, `row`, `column`, `spatial_block`) are strictly excluded from the feature matrix `X`.
  - Target-derived variables (`lst`, `observed_suhii`, `rural_reference`) are strictly excluded from features.
  - Verified by `test_pipeline.py:test_models_spatial_evaluation`:
    ```python
    assert "lst" not in a["features"] and "observed_suhii" not in a["features"]
    ```

#### C. Spatial Cross-Validation & Spatial Separation
Spatial autocorrelation can cause severe data leakage if random k-fold splitting is used. The codebase enforces strict spatial separation via two paths:
1. **Regular Grid Baseline Partitioning (`ml.py:159-175`)**:
   - For 18 × 18 grids, zones are split into 6 longitude-based blocks (`spatial_block = column // 3`):
     - **Training**: Blocks 0, 1, 2 (western 9 columns; 162 zones = 50.0%)
     - **Validation**: Block 3 (columns 9-11; 54 zones = 16.7%)
     - **Spatial Buffer**: Block 4 (columns 12-14; 54 zones = 16.7%) — **CRITICAL**: Zones in Block 4 are completely withheld from training, validation, and testing to eliminate spatial autocorrelation leakage across boundaries!
     - **Test**: Block 5 (eastern 3 columns 15-17; 54 zones = 16.7%)
2. **Generalized Spatial Partitioning for Arbitrary GeoJSON (`ml.py:58-151: assign_spatial_partitions`)**:
   - Extracts zone centroids.
   - Calculates spatial variance along longitude vs. latitude to identify the primary axis of spatial dispersion.
   - For $N \ge 15$: Performs 6-cluster 2D KMeans sorted along the primary spatial axis (with automatic fallback to 6 balanced spatial quantiles if clusters are degenerate). Assigns blocks 0-2 to training, block 3 to validation, block 4 to spatial buffer, and block 5 to test.
   - For $8 \le N < 15$: 4-block spatial quantiles (2 train, 1 val, 1 test).
   - For $5 \le N < 8$: Spatial ranking along primary axis ($N-2$ train, 1 val, 1 test).

#### D. Metrics Tracked & Prediction Uncertainty
- Tracked metrics for both validation and test partitions:
  - $R^2$ (`r2_score`)
  - $\text{RMSE} = \sqrt{\text{mean\_squared\_error}}$
  - $\text{MAE} = \text{mean\_absolute\_error}$
- Prediction Interval:
  - Calculated as the empirical 90th percentile of absolute validation residuals:
    ```python
    val_errors = np.abs(frame.loc[val, "observed_suhii"].to_numpy() - model.predict(Xval))
    interval = float(np.quantile(val_errors, 0.90))
    ```
  - Yields conformal-like empirical prediction bounds: `[predicted_suhii - interval, predicted_suhii + interval]`.

#### E. Spatial XAI & TreeSHAP
- **Local Explanations (`ml.py:296-331`)**:
  - Exact TreeSHAP computed via `shap.TreeExplainer(model)(X)`.
  - Produces an exact additive breakdown for each zone:
    $$\text{predicted\_suhii} = \text{shap\_base} + \sum_{j=1}^{12} \text{shap}_{j}$$
  - Additivity is mathematically guaranteed and unit-tested (`test_pipeline.py:test_shap_additivity` verifies difference $< 10^{-4}$).
- **Global Explanations**:
  - Global feature importance ranked by mean absolute SHAP value:
    $$\text{importance}_j = \frac{1}{N} \sum_{i=1}^N |\text{shap}_{i, j}|$$

---

### 1.5 Intervention Simulation & Optimization Findings

#### A. Implemented Intervention Categories (`planning.py:6-87`)
Eight discrete physical cooling interventions are implemented:
| Key | Name | Surface | Cooling per 10% Coverage (°C) | Water Req. ($m^3/\text{day}$ per % per $km^2$) | Vegetative | CapEx ($/m^2$) | OpEx ($/m^2/\text{yr}$) | Cost per 1% ($/km^2$) |
|---|---|---|---|---|---|---|---|---|
| `trees` | Urban trees | ground | 0.35 | 20 | True | $5.50 | $0.50 | $55,000 |
| `vegetation` | Native vegetation | ground | 0.25 | 10 | True | $20.00 | $2.00 | $200,000 |
| `parks` | Pocket parks | ground | 0.30 | 15 | True | $50.00 | $5.00 | $500,000 |
| `cool_roofs` | Cool roofs | roof | 0.28 | 0 | False | $12.00 | $1.20 | $120,000 |
| `pavements` | Reflective pavements | road | 0.18 | 0 | False | $30.00 | $2.50 | $300,000 |
| `corridors` | Green corridors | ground | 0.32 | 15 | True | $45.00 | $4.00 | $450,000 |
| `roof_gardens` | Rooftop gardens | roof | 0.22 | 12 | True | $100.00 | $8.00 | $1,000,000 |
| `water` | Water-based cooling | ground | 0.20 | 40 | False | $35.00 | $6.00 | $350,000 |

#### B. Physical Capacity and Feasibility Constraints (`planning.py:165-239`)
- **Surface Area Limits**: Ground treatments cannot exceed `available_land_pct`, roof treatments cannot exceed `roof_pct`, and road treatments cannot exceed `road_pct`.
- **Protected Land**: Ground interventions are strictly forbidden on protected zones (`cap = 0` if `zone["protected"] == True`).
- **Roof Mutual Exclusivity**: `cool_roofs` and `roof_gardens` cannot co-exist in the same zone.
- **Vegetation Ceiling**: Total added vegetative coverage across all types cannot exceed `max_vegetation_pct` (default 40%).
- **Water Limit**: Total water consumption cannot exceed `water_limit` ($m^3/\text{day}$).
- **Cooling Saturation**: Combined cooling combines linearly up to a physical ceiling of 3.0°C (`cooling = min(3.0, cooling)`).
- **Tree Canopy Conversion**: Translates physical tree counts into zone area percentage assuming an average canopy crown of $28.0\,m^2$ per tree (`CANOPY_M2_PER_TREE = 28.0`).

#### C. Google OR-Tools CP-SAT Formulation (`planning.py:241-409`)
- **Discrete Decision Variables**:
  - Integer variables representing allocation in 5-percentage-point increments:
    ```python
    levels = model.NewIntVar(0, int(cap // 5), f"{z}-{key}")
    ```
  - Mutually exclusive roof boolean:
    ```python
    roof_kind = model.NewBoolVar(f"{z}-roof-kind")
    model.Add(local["cool_roofs"] == 0).OnlyEnforceIf(roof_kind)
    model.Add(local["roof_gardens"] == 0).OnlyEnforceIf(roof_kind.Not())
    ```
- **Cooling Variable & Saturation**:
  - Integer cooling in millidegrees (0 to 3000 m°C, i.e., 3.0°C cap):
    ```python
    raw = sum(v * round(INTERVENTIONS[k]["cooling_per_10pct"] * 500) for k, v in local.items())
    cool = model.NewIntVar(0, 3000, f"{z}-cooling")
    model.AddMinEquality(cool, [raw, 3000])
    ```
- **Objective Function**:
  - Maximizes population- and vulnerability-prioritized cooling:
    ```python
    priority = max(
        1,
        round(
            p["population"]
            * (0.2 + p["elderly_share"])
            * max(0.2, p.get("predicted_suhii", p.get("observed_suhii", 2.0)))
        ),
    )
    objectives.append(cool * priority)
    model.Maximize(sum(objectives))
    ```
- **Solver Constraints Enforced**:
  1. Surface capacity per surface type (ground, roof, road)
  2. Maximum vegetative expansion limit (`max_vegetation_pct`)
  3. Total municipal water consumption limit (`sum(water_terms) <= int(water_limit)`)
  4. Minimum mean cooling requirement (`sum(cool_terms) >= math.ceil(min_cooling * 1000 * len(zones))`)
  5. Conditional financial budget constraint (`sum(cost_terms) <= int(budget_limit)` if enabled)
- **Sensitivity Analysis**:
  - Automatically runs an alternate scenario at 50% water budget (`result["alternative"] = {"label": "Half-water alternative", ...}`) to show water-cooling elasticity.

#### D. Budget Constraints: Current Implementation vs. How to Remove / Make Unconstrained
1. **Current Implementation**:
   - Financial budget was added in Milestone 2 (`planning.py:273-274`, `planning.py:316-317`, `schemas.py:91-96`).
   - Costs per level: `cost_per_level = int(round(5 * spec["cost_per_pct"] * p["area_km2"]))`.
   - Solver enforcement:
     ```python
     if budget_limit is not None and budget_enforced:
         model.Add(sum(cost_terms) <= int(budget_limit))
     ```
   - In `simulate()`, a violation is added only if `budget_enforced and budget_limit is not None and cost > budget_limit + 1e-6`.
   - In `OptimizationRequest`, `budget_enforced: bool = False` (defaults to False), and `budget_limit: float | None = None`.
2. **How Budget Constraints Can Be Removed or Made Unconstrained**:
   - **Mode 1 (Operational Unconstraint via Existing Configuration)**:
     - By default, because `budget_enforced` defaults to `False` and `budget_limit` defaults to `None`, the optimizer is ALREADY unconstrained by budget unless a caller explicitly passes `budget_enforced=True`.
   - **Mode 2 (Complete Architectural Decoupling from Solver)**:
     - If the project requires budget constraints to be permanently removed from the optimization problem:
       1. In `planning.py:optimize()`, delete `if budget_limit is not None and budget_enforced: model.Add(sum(cost_terms) <= int(budget_limit))`.
       2. Retain `total_cost` and `selections[].estimated_cost` purely as calculated **output metrics** (descriptive / informational financial reporting), rather than input constraints.
       3. In `schemas.py:OptimizationRequest`, remove `budget_limit` and `budget_enforced` as constraint fields.
       4. In `planning.py:simulate()`, remove the budget violation check from `violations`.

---

## 2. Logic Chain

1. **Premise 1 (Module Structure)**: The prompt requested inspection of `sources.py`, `geospatial.py`, `satellite.py`, `demographics.py`, `risk.py`, `ml.py`, `features.py`, `xai.py`, `planning.py`, `optimization.py`.
   - *Observation*: Only `sources.py`, `data.py`, `ml.py`, `planning.py`, `ai.py`, and `state.py` currently exist in `backend/app/services/`.
   - *Deduction*: The other files (`geospatial.py`, `satellite.py`, `demographics.py`, `risk.py`, `features.py`, `xai.py`, `optimization.py`) represent the planned modularization targets assigned to Agents 1, 2, 3, and 4 in `ORIGINAL_REQUEST.md`. Currently, all logic is working and consolidated in the existing files.

2. **Premise 2 (Earth Observation Credibility)**: Live satellite data ingestion must not use mock or synthetic data when external APIs fail.
   - *Observation*: `sources.py` enforces strict live adapters (HTTP errors raised directly, no fallback mock data, `"synthetic": False`).
   - *Observation*: Sentinel-2 COG reads use windowed `rasterio.vrt.WarpedVRT` into EPSG:6933 at 100 m with SCL cloud/shadow filtering.
   - *Observation*: Earth Engine uses Level-2 Landsat 8/9 with `QA_PIXEL` and `QA_RADSAT` masking, computing LST in Celsius.
   - *Deduction*: The satellite ingestion architecture has strong mathematical rigor for remote sensing. The primary gap is that live raster data are not yet automatically converted into predictive zone features (the predictive model currently trains on seeded synthetic datasets).

3. **Premise 3 (Demographic & Risk Framework)**: The risk calculation must account for human vulnerability, not just hazard.
   - *Observation*: `risk()` computes $100 \times \text{Hazard}^{w_H} \times \text{Exposure}^{w_E} \times \text{Vulnerability}^{w_V}$ using population density and elderly share.
   - *Observation*: WorldPop and GHSL STAC endpoints return catalog metadata; live population rasters are not yet sampled at the zone level.
   - *Deduction*: The mathematical risk model is fully compliant with IPCC standards, but live demographic data ingestion is currently limited to discovery catalogs.

4. **Premise 4 (Spatial ML Rigor)**: Random split in spatial data leads to spatial autocorrelation leakage.
   - *Observation*: `ml.py` uses 6 spatial blocks with Block 4 acting as an explicit spatial buffer between training/validation and testing.
   - *Observation*: Model tournament chooses the lowest validation RMSE among Random Forest, XGBoost, and LightGBM.
   - *Observation*: Additive TreeSHAP is calculated directly on tree models.
   - *Deduction*: The ML pipeline avoids spatial leakage by design.

5. **Premise 5 (CP-SAT Optimization & Budget)**: Discrete optimization must handle non-linear saturation, surface capacity, water, and budget.
   - *Observation*: CP-SAT solves 5-percentage-point increments across 8 interventions with 3.0°C saturation, mutual exclusivity for roofs, ground protection, and water limits.
   - *Observation*: Budget constraints are gated behind `budget_enforced: bool = False`.
   - *Deduction*: The CP-SAT model is sound, and removing budget constraints can be accomplished either by leaving `budget_enforced=False` or by cleanly decoupling cost from solver constraints.

---

## 3. Caveats

1. **Earth Engine Credentials**: Live execution of `sources.py:earth_engine()` and `sources.py:supplementary_earth_engine()` requires `EARTH_ENGINE_PROJECT` and Google Application Default Credentials. In test environments without credentials, tests mock `ee.Initialize` and `ee.ImageCollection`.
2. **Sentinel-2 S3 COG Network Access**: Reading Element 84 COGs via `rasterio.open(href)` requires egress to AWS S3. In offline or sandboxed test runs, mocked responses are used.
3. **Census of India & Real Socioeconomic Data**: While WorldPop and GHSL catalogs are integrated, Census of India tabular data (wards, slum settlements, AC access) are not yet integrated; synthetic elderly share is currently used as the vulnerability proxy.
4. **Current Test Status**: All 175 existing unit, integration, and challenger tests in `backend/tests/` are currently passing with 0 failures.

---

## 4. Conclusion

The scientific, ML, XAI, and optimization core of Heatwise is technically sophisticated and architecturally sound:
1. **Remote Sensing**: Robust implementations exist for Landsat Collection 2 L2 thermal LST, Sentinel-2 SCL cloud masking, COG WarpedVRT windowing into EPSG:6933, and MODIS MOD11A2.
2. **Demographics & Vulnerability**: A complete IPCC AR5/AR6 Hazard × Exposure × Vulnerability multiplicative framework is implemented, with WorldPop and GHSL STAC discovery adapters.
3. **Machine Learning & Spatial XAI**: A 3-model tournament (RF, XGBoost, LightGBM) is implemented with 6-block spatial separation (including an explicit spatial buffer fold to prevent autocorrelation leakage) and exact additive TreeSHAP explainability.
4. **CP-SAT Optimization**: A discrete combinatorial optimization formulation in Google OR-Tools CP-SAT maximizes equity-weighted cooling across 8 interventions under physical surface capacities, water budgets, and configurable budget constraints. Budget constraints are already modular and can either be disabled via `budget_enforced=False` or fully decoupled from solver constraints to serve purely as output cost metrics.
5. **Upcoming Modularization**: The service layer is currently consolidated across `sources.py`, `data.py`, `ml.py`, and `planning.py`. The planned delegation to Agents 1, 2, 3, and 4 to break these into `geospatial.py`, `satellite.py`, `demographics.py`, `risk.py`, `features.py`, `xai.py`, and `optimization.py` will establish clean single-responsibility modules without altering any existing contracts.

---

## 5. Verification Method

To independently verify the observations and findings in this report:

1. **Verify Backend Test Suite Pass (175 tests)**:
   ```powershell
   python -m pytest backend/tests/
   ```
   *Expected output*: 175 passed in ~45 seconds.

2. **Verify ML Pipeline, Spatial CV, and TreeSHAP Additivity**:
   ```powershell
   python -m pytest backend/tests/test_pipeline.py -v
   ```
   *Expected output*: 6 passed, verifying 162/54/54/54 spatial block partitioning, TreeSHAP exact additivity ($|\text{shap\_base} + \sum \text{shap} - \text{pred}| < 10^{-4}$), and physical simulation constraints.

3. **Verify Data Source Adapters, Cloud Masking, and NASA POWER Fill Policies**:
   ```powershell
   python -m pytest backend/tests/test_sources.py -v
   ```
   *Expected output*: 34 passed, verifying Sentinel-2 cloud filtering, NASA POWER fill-value masking, Open-Meteo series aggregation, and Element 84 COG parsing.

4. **Verify CP-SAT Optimizer Budget Invariants & Extremes**:
   ```powershell
   python -m pytest backend/tests/test_challenger_m2_api_budget.py -k "test_cpsat" -v
   ```
   *Expected output*: All CP-SAT budget edge case tests pass ($0 budget, tight budget, infinite budget, infeasibility on positive cooling with $0 budget).

5. **Inspect Key File Locations**:
   - Satellite & Ingestion: `backend/app/services/sources.py:420-769`
   - Data & Spectral Indices: `backend/app/services/data.py:168-193`
   - ML & Spatial Partitions: `backend/app/services/ml.py:58-262`
   - TreeSHAP Explainability: `backend/app/services/ml.py:296-338`
   - IPCC Heat-Risk Framework: `backend/app/services/planning.py:140-163`
   - CP-SAT Optimizer & Budget: `backend/app/services/planning.py:241-409`
