# DISPATCH — 2026-11-10T12:10:17Z

## 2026-11-10T12:10:17Z
Create seven specialized agents with clearly separated responsibilities. A lead orchestrator must coordinate their work, establish shared interfaces, review implementation and run integration tests. Transform the existing Heatwise project into a production-oriented, AI-powered Urban Climate Intelligence, Heat Risk Assessment and Mitigation Planning Platform, including a complete world-class frontend redesign and real-world data and model overhaul for city planners, municipal authorities, environmental analysts, and urban researchers.

Working directory: d:\Urban-Heat-Resilience-AI
Integrity mode: development

## Requirements

### R1. Complete World-Class Frontend Redesign and Climate Intelligence UI
Completely transform the existing Heatwise frontend into a premium, modern, dark-first climate-intelligence platform with Palantir-style geospatial intelligence and Linear-level interface precision. Implement an application shell with collapsible navigation and a top command bar, redesign all pages (Overview Command Center, Live Environmental Map, Heat Analysis, Environmental Analysis, Heat Risk & Vulnerability, Explainable AI, Mitigation Planning, Intervention Optimization, AI Climate Assistant, Reports), implement purposeful animations, micro-interactions, responsive layouts across desktop and mobile, and connect every page to backend APIs without fabricating data.

### R2. Earth Observation and Real Satellite Data Pipeline
Replace synthetic satellite and environmental inputs with an actual data acquisition and preprocessing pipeline. Ingest Landsat 8/9 Collection 2 Level-2 Surface Temperature rasters, Sentinel-2 Level-2A spectral indices (NDVI, NDWI, NDBI), and support MODIS/ESA WorldCover/NASA SRTM using Google Earth Engine, Rasterio, and GeoPandas. Implement spatial clipping, cloud masking, spatial aggregation into analytical zones, metadata provenance recording, and caching. Distinguish satellite-observed surface temperature from air temperature and model predictions; do not silently replace failed satellite acquisitions with synthetic data. Select the primary target city based on satellite data coverage and available stations.

### R3. Live Weather, Air Quality, and Groundwater Ingestion
Integrate genuine environmental observations and forecasts: Open-Meteo for current weather, daily forecasts, and historical trends; OpenAQ API v3 / CPCB for air pollution monitoring stations (PM2.5, PM10, NO2, SO2, O3, CO) with timestamps and station distance; CGWB / India-WRIS for groundwater depth and trends. Differentiate forecasts from observations, station readings from spatial interpolation, and groundwater depth from surface water or soil moisture. Test with available local environment credentials; for unconfigured external services, implement the integration with graceful no-data handling and setup instructions rather than fabricating measurements.

### R4. Geospatial Platform and Interactive Mapping System
Build a reusable geospatial mapping system (using Leaflet or MapLibre with OSM-compatible tiles) supporting real geographic coordinates and multi-layer visualization: Land Surface Temperature, predicted surface temperature, SUHII, NDVI/vegetation, built-up density, land cover, air-quality stations, weather stations, groundwater stations, heat-risk zones, population exposure, and proposed interventions. Provide city search, area/zone selection, layer toggles, physical-unit legends, zone inspection details, time-period filters, and robust no-data/error states.

### R5. Defensible Machine Learning, Climate Analytics, and Explainable AI
Define explicit prediction targets (LST and SUHII relative to a rural reference). Implement and compare Random Forest, XGBoost, and LightGBM using scientifically justified features and spatial/temporal validation (avoiding spatial data leakage). Evaluate models using R², MAE, RMSE, bias, residual analysis, and spatial error maps. Implement genuine TreeSHAP/SHAP explanations (global feature importance, zone-specific explanations, base value, and contributions in understandable terms) without conflating SHAP with causal cooling impacts.

### R6. Heat Risk Assessment and Physical Intervention Optimization Engine
Develop a transparent heat-risk framework decomposing hazard (surface heat, air temperature, duration), exposure (population, residential density, land use), and vulnerability (socioeconomic, age, access indicators from WorldPop, GHSL, census) without substituting population density for vulnerability. Implement an intervention simulator for urban greening, cool surfaces, and permeable infrastructure with literature-grounded cooling mechanisms and uncertainty. Build an optimizer (e.g. OR-Tools CP-SAT) enforcing physical, land-use, and water constraints to generate feasible intervention combinations and spatial priority plans without any financial budget constraints or objectives.

### R7. Backend Architecture, Typed API Contracts, and Grounded AI Assistant
Stabilize and refactor the FastAPI backend with clean service separation, Pydantic validation, PostgreSQL/PostGIS (or explicitly labelled SQLite dev fallback), structured logging, centralized exception handling, caching, and health checks. Audit and fix all frontend API routes, CORS issues, and response models. Implement a functional AI climate assistant (Groq and Google Gemini with provider fallback) answering questions strictly grounded in actual backend data with source citations, displaying clear errors on failure rather than synthetic responses.

## Verification Resources
Existing test suites and evaluation scripts within the repository (`d:\Urban-Heat-Resilience-AI`).

## Acceptance Criteria

### Data Ingestion and Integrity
- [ ] Real Landsat surface-temperature data is retrieved and processed for the selected city.
- [ ] Sentinel-2 spectral indices (NDVI, NDWI, NDBI) are calculated correctly from valid imagery.
- [ ] Current weather observations and forecasts are retrieved from Open-Meteo with actual observation timestamps.
- [ ] Air-quality measurements are retrieved from OpenAQ/CPCB and attributed to real monitoring stations with timestamps.
- [ ] Groundwater observations are retrieved from verified sources with recorded observation dates where available.
- [ ] Every dataset displays provenance metadata (source, timestamp, spatial resolution, units, and data freshness).
- [ ] No synthetic or placeholder data silently enters real-data results; any fallback or mock data is isolated and prominently labelled as demonstration data.
- [ ] External services without configured credentials degrade gracefully with clear no-data indicators and setup documentation.

### Geospatial and Mapping Experience
- [ ] Map renders reliably across all screen sizes without blank panels, broken layouts, or arbitrary grid placements.
- [ ] City and zone selection dynamically updates the map view and analytical context.
- [ ] Map layer toggles function smoothly with physical-unit legends and opacity controls.
- [ ] Clicking a spatial zone displays actual associated environmental and risk data.
- [ ] Unavailable layers display explicit no-data states explaining what is missing.

### Machine Learning and Explainability
- [ ] Model training and evaluation use documented real observations with spatial or temporal cross-validation.
- [ ] Model performance metrics (R², MAE, RMSE) trace to actual datasets without fabricated high accuracy.
- [ ] TreeSHAP/SHAP explanations produce valid feature contributions and base values for individual zones.
- [ ] Clear distinction is maintained between satellite-observed LST, air temperature, and model-predicted surface temperature.

### Risk Assessment and Mitigation Planning
- [ ] Heat risk transparently decomposes hazard, exposure, and vulnerability without substituting population density for vulnerability.
- [ ] Intervention simulator uses literature-grounded cooling mechanisms and displays uncertainty ranges.
- [ ] Optimization engine enforces physical and environmental constraints without any financial budget objectives or constraints.
- [ ] Scenario results are explicitly labelled as hypothetical estimates.

### AI Assistant and Backend Stability
- [ ] Backend starts cleanly with typed Pydantic models, structured logging, and health checks.
- [ ] Frontend API routes connect cleanly without CORS or endpoint prefix errors.
- [ ] AI assistant (Groq / Gemini) generates grounded answers referencing actual backend data and handles provider downtime with user-facing errors.

### Frontend Quality and System Verification
- [ ] Complete UI redesign following dark-first climate-intelligence design system across all 10 navigation views.
- [ ] Responsive design functions without horizontal overflow on desktop, tablet, and mobile screens.
- [ ] Frontend production build succeeds (`npm run build` or equivalent).
- [ ] Existing frontend and backend test suites pass.
