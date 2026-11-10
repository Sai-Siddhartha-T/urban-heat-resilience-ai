## 2026-11-08T22:06:13Z
You are Explorer M2-1: Backend APIRouter Modularization & Lifespan Caching Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_1

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read previous survey findings:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_backend_2\survey_backend.md

Your mission for Milestone 2:
1. Design the modularization of `backend/app/main.py` (602 lines) into discrete FastAPI `APIRouter` modules in `backend/app/routes/`:
   - `routes/heat.py` (`/api/heat/map`, `/api/heat/hotspots`, `/api/heat/predict`)
   - `routes/models.py` (`/api/models`, `/api/models/train`, `/api/xai/explain`, `/api/xai/importance`)
   - `routes/simulation.py` (`/api/interventions`, `/api/simulation/run`, `/api/simulation/results`)
   - `routes/optimization.py` (`/api/optimization/run`, `/api/optimization/results`)
   - `routes/risk.py` (`/api/risk/analyze`)
   - `routes/data.py` (`/api/data/status`, `/api/data/records`, `/api/data/series`, `/api/data/ingest`)
   - `routes/ai.py` (`/api/ai/chat`)
   - `routes/reports.py` (`/api/reports/*`)
   - Keep app entrypoint, middleware, exception handlers, and router inclusions in a clean, compact `main.py`.
2. Design the ML state caching and fast startup optimization:
   - Eliminate the 540-tree cold-start training delay on app lifespan.
   - Support model persistence / disk caching in `load_or_train()`.
   - Add support for `PREWARM_STATE=0` environment variable to skip cold-start training during unit testing with TestClient.
3. Provide complete drop-in blueprints in `analysis.md` and `handoff.md`.
4. Send completion message to orchestrator. Do not modify source code.
