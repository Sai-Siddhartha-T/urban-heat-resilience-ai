## 2026-11-09T13:17:21Z

You are the Data & ML Pipeline Explorer.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\survey_data_ml_explorer\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md

You MUST read ORIGINAL_REQUEST.md first.

Your mission in this survey phase:
Investigate all scientific, data ingestion, ML, spatial XAI, and optimization modules in `backend/app/services/`.
Specifically explore and report on:
1. Satellite Data & Earth Observation:
   - Inspect `backend/app/services/sources.py`, `backend/app/services/geospatial.py`, `backend/app/services/satellite.py`.
   - How are satellite data currently generated or retrieved (synthetic vs real)?
   - Look at Earth Engine integration, Landsat 8/9 LST, Sentinel-2 indices (NDVI, NDWI, NDBI, NDBaI), MODIS MOD11A2, cloud masking, raster reprojection.
2. Demographic Data & Vulnerability:
   - Inspect `backend/app/services/demographics.py`, `backend/app/services/risk.py`.
   - What data sources are currently used or mocked (WorldPop, Census of India, GHSL)?
   - How are demographic features joined to geographic zones? How is the heat-risk framework implemented (Hazard x Exposure x Vulnerability)?
3. Machine Learning & Spatial XAI:
   - Inspect `backend/app/services/ml.py`, `backend/app/services/features.py`, `backend/app/services/xai.py`.
   - What models are implemented (Random Forest, XGBoost, LightGBM)?
   - How are features configured? Is there spatial cross-validation / spatial separation to avoid data leakage?
   - How are SHAP explanations generated? What metrics are tracked?
4. Intervention Simulation & Optimization:
   - Inspect `backend/app/services/planning.py`, `backend/app/services/optimization.py`.
   - What intervention categories are implemented?
   - How are budget constraints currently implemented? How should they be removed per task requirements?
   - Is Google OR-Tools CP-SAT used? What is the current optimization formulation and objective?

Deliverable:
Write a comprehensive survey report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\survey_data_ml_explorer\handoff.md`
following the standard handoff structure (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
When done, message the orchestrator with your findings.
