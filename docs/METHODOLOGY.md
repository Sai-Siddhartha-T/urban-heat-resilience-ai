# Heatwise methodology and limits

## Provenance
The default analysis is deterministic **synthetic data**, generated with NumPy seed 42. The displayed 15 May 2025 date is a sample label, not a satellite acquisition. Each city has 324 approximately 1 km² cells. Coordinates use WGS84; grid dimensions are an approximation (0.009° latitude with a cosine longitude correction). Satellite and weather imports are separate persisted evidence, not substituted into synthetic models.

The sample combines synthetic vegetation, water, built-up and bare-soil indices, population, building density, weather, soil moisture and land cover. The synthetic SUHII target uses a documented function in `backend/app/services/data.py` plus seeded noise. Metrics measure recovery of that relationship, not field accuracy. Synthetic population and elderly share do not describe real residents.

## Surface heat and rural reference
SUHII = urban LST − rural reference LST. Surface temperature is **not** air temperature or human thermal comfort. The demo reference defaults to 33°C and is configurable when rebuilding the sample. Changing it shifts absolute LST while holding the generated surface-heat difference constant. Real analysis requires a documented, contemporaneous rural reference with comparable elevation, observation time, land cover selection, and quality masks. Reference choice can materially change SUHII.

## Live geospatial path
The tested public route searches Earth Search's Sentinel-2 L2A catalog, retains scenes with cloud cover below 20%, reads red/NIR/green/SWIR/SCL COG windows, applies each asset's radiometric scale/offset, and retains SCL classes 4–7. Every band is reprojected to the same EPSG:6933 100 m grid (32×32 cells, centered on the request). Continuous bands use average resampling; SCL uses nearest-neighbor. Invalid pixels become null. Spectral indices are computed after alignment.

NDVI=(NIR−red)/(NIR+red); NDWI=(green−NIR)/(green+NIR); NDBI=(SWIR−NIR)/(SWIR+NIR). A zero denominator is missing, not zero. NDBaI=(normalized SWIR−normalized thermal)/(normalized SWIR+normalized thermal) is provided as a utility but is **not** calculated from raw reflectance and Celsius. It requires a documented, commensurate radiometric normalization. Satellite-derived NDBaI is unavailable in the current live pipeline.

Sentinel-2 has no thermal band and does not supply LST. Live optical data is not passed to the synthetic model. Actual acquisition dates, scene IDs, source grid, processing grid, and quality methods are retained.

Earth Engine adapters require project credentials. Landsat L2SP ST_B10 uses 0.00341802 K/DN +149 K, converted to Celsius; QA_PIXEL bits 0–5 and radiometric saturation are excluded. Sentinel harmonized optical data uses SCL filtering. MOD11A2 retains good mandatory QA and LST-error classes ≤1, scales by 0.02 K, and averages eight-day daytime composites. ESA WorldCover 2021 and SRTM February 2000 retain their distinct observation periods. These are separately sampled at 1 km in EPSG:6933, never implicitly fused. Categorical WorldCover sampling is not a coverage fraction. Native-resolution limitations remain.

## Models and uncertainty
Features: NDVI, NDWI, NDBI, NDBaI, building density, population density, air temperature, relative humidity, rainfall, solar radiation, soil moisture and categorical land cover encoded as an integer. The synthetic dataset's land-cover classes are binary.

Western 9 columns: 162 training cells. Next 3 columns: 54 validation cells. Next 3: 54 buffer cells. Eastern 3: 54 test cells. Median imputation is fitted on training only. Models share the same split. Model selection uses validation RMSE; test results are reported independently. The selected model is retained without refitting on validation/test. No coordinates, LST, or target-derived features enter predictors. The holdout guards spatial adjacency but a single spatial split does not establish transferability.

RF: 180 trees, minimum leaf size 2. XGBoost: 180 estimators, depth 3, learning rate 0.04. LightGBM: 180 estimators, depth 4, 12 leaves, learning rate 0.04. Seeds are 42. Models and imputers are persisted with joblib; only locally generated artifacts should be loaded.

The displayed range adds/subtracts the validation residuals' 90th-percentile absolute error. It is an empirical band, **not a guaranteed 90% confidence interval**. No real-world or temporal coverage claim is made.

TreeSHAP calculates actual per-zone contributions and mean absolute global importance. Base value plus contributions reconstructs the prediction. SHAP is associative, not causal.

## Risk
H=clip(SUHII/8,0,1); E=clip(population/km²/25,000,0,1); V=clip(elderly share/0.25,0,1).
Risk score=100×H^wH×E^wE×V^wV. Exponents default to 1, configurable from 0.1 to 3. High ≥20, moderate ≥8, low below 8. These thresholds and denominators are illustrative. They are neither epidemiological calibrations nor universal heat-health cutoffs. Socioeconomic conditions, health status and cooling access remain explicitly missing. Population density is not used as vulnerability.

## Hypothetical intervention effects
All coefficients below are **uncalibrated demonstration assumptions**, not literature-backed estimates. Coverage means percentage points of total zone area. Effects are independent of SHAP.

| Intervention | Surface | Cooling °C per 10 percentage points | Water m³/day per percentage point per km² |
|---|---|---:|---:|
| Trees | Ground | 0.35 | 20 |
| Native vegetation | Ground | 0.25 | 10 |
| Parks | Ground | 0.30 | 15 |
| Cool roofs | Roof | 0.28 | 0 |
| Reflective pavement | Road | 0.18 | 0 |
| Green corridors | Ground | 0.32 | 15 |
| Roof gardens | Roof | 0.22 | 12 |
| Water cooling | Ground | 0.20 | 40 |

Combined cooling is linear, capped at 3°C; ±40% is a sensitivity range, not a statistical interval. This simplified model excludes microclimate transport, seasonality, maturity of trees, and interactions. It can produce negative scenario SUHII (surface below the rural reference), which does not mean subzero temperature. No direct health-benefit claim is made.

## Optimization
OR-Tools CP-SAT selects integer multiples of 5 percentage points across the highest-priority five zones by default (API accepts up to 30 explicit zones). Shared ground/roof/road capacity, protected ground exclusions, per-zone added vegetation, cool-roof/roof-garden incompatibility, global water supply and optional minimum mean cooling are enforced. Ground use can be further limited. Cooling is represented in thousandths of a degree to preserve the simulator's coefficients exactly. Solver status distinguishes optimal, feasible, infeasible and timeout/unknown.

The objective maximizes hypothetical cooling weighted by population × (0.2+elderly share) × max(0.2,SUHII), a prioritization proxy. It does not optimize budgets. Population in selected zones is not people protected. The alternative halves available water and removes the minimum cooling target. Infeasibility reports the conflicting class of constraints, not a mathematically minimal unsatisfiable core.

## AI decision support
Groq and Gemini receive actual predictions, SHAP, risk, constraints, saved scenarios and the latest optimization. Model names and keys are server-side environment variables. Availability is checked with the provider model-list API. JSON outputs must pass Pydantic validation, cite existing evidence keys, contain no digits in summary/findings, and only propose actions passing a basic per-zone feasibility check. These checks reduce unsupported claims; they do not prove semantic correctness. Provider pagination and unusual response formats may trigger fallback.

Missing credentials, network errors, invalid JSON or unsupported claims fall back to the other provider, then a clearly labeled deterministic evidence summary. The local template does not provide general conversational reasoning and is never called an LLM response. Production deployments still require expert review and stronger claim-level validation.
