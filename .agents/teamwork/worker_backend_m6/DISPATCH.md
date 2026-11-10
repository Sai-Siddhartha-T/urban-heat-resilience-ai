## 2026-11-09T13:32:03Z
You are AGENT 6: Backend Architecture, API and Database Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_backend_m6\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting.

Your exclusive write ownership:
- `backend/app/services/risk.py` (create new module)
- `backend/app/services/planning.py` (re-export risk)
- `backend/app/routes/risk.py` (update import)
- `backend/app/services/state.py` (update import)
- `backend/app/routes/heat.py`, `backend/app/routes/models.py`, `backend/app/routes/simulation.py`, `backend/app/routes/` router definitions
- `backend/app/main.py`
- `backend/app/db.py`
- Relevant backend integration tests

Objectives & Tasks:
1. API Route Consistency:
   - Frontend `apiClient.ts` calls `fetch("/api" + path)`.
   - Backend routes currently serve `/api/cities`, `/api/overview`, etc.
   - 3 routers (`heat.py`, `models.py`, `simulation.py`) hardcode `/api` on decorators, while 5 routers use `APIRouter(prefix="/api/...")`.
   - Harmonize router prefixing so route declarations are consistent, clean, and maintainable without changing runtime endpoint URLs.
   - Ensure both `/api/cities` and any direct requests work properly.
2. Missing Risk Module:
   - Create `backend/app/services/risk.py` containing the `risk(p, weights=(1, 1, 1))` implementation, calculation of Hazard, Exposure, Vulnerability, and metadata.
   - In `backend/app/services/planning.py`, import and re-export `risk`: `from app.services.risk import risk` to preserve backward compatibility.
   - Update imports in `backend/app/routes/risk.py` and `backend/app/services/state.py` to import from `app.services.risk`.
3. Database and Environment Reliability:
   - Verify `backend/app/db.py` handles SQLite local development and PostgreSQL/PostGIS.
   - Ensure optional environment variables (`EARTH_ENGINE_PROJECT`, `GROQ_API_KEY`, `GEMINI_API_KEY`, etc.) fail gracefully without crashing startup.
4. Validation & Test Execution:
   - Run the complete backend test suite: `pytest -q`
   - Ensure all 175+ tests pass with 0 regressions.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_backend_m6\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method (with exact test execution results).
When done, message the orchestrator.
