# Dispatch Instructions

## 2026-11-08T20:12:19Z
MASTER PROMPT — AI-POWERED URBAN HEAT RESILIENCE & MITIGATION PLATFORM

Improve the project and make it even better and fix things across backend, frontend, ML pipeline, data integrations, and testing based on the master prompt.

Relevant earlier context:
The project is at d:\Urban-Heat-Resilience-AI.
Current state:
- FastAPI backend with 24 endpoints, SQLite/PostGIS, ML pipeline (RF, XGBoost, LightGBM) with spatial validation and TreeSHAP.
- 8 intervention simulation models + OR-Tools CP-SAT optimizer.
- React/TypeScript frontend (currently a 2,164-line monolithic App.tsx that needs splitting into modular components/pages, client routing or clean tab routing, better TypeScript interfaces, richer charts, zone comparison, weather time-series integration).
- Data adapters for Open-Meteo, Sentinel-2 STAC/COG, OSM, WorldPop, Earth Engine, OpenAQ.
- All existing tests pass (16 tests in backend/tests).
- Improve modularity, UI/UX, TypeScript types, add missing features, ensure all tests pass and frontend builds cleanly without errors.

---
Execution Context:
- Working directory: d:\Urban-Heat-Resilience-AI
- Orchestrator state folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1_gen2
- Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
- Sentinel conversation ID: 17b968e2-e6c9-4911-b904-8dfefbb98722
