## 2026-11-08T22:43:22Z
You are Explorer M2-1 (Gen 2): Backend Modularization & Fast Startup Specialist for Milestone 2.

Your predecessor was interrupted by a transient network error. Read your predecessor's progress and findings at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_1\progress.md
Key finding already established by predecessor:
1. `sample_data()` sets `"generated_at": datetime.now(timezone.utc).isoformat()` dynamically every invocation.
2. `load_or_train()` checks `a["metadata"]["generated_at"] == data["metadata"]["generated_at"]`. Because `generated_at` differs on every call, cached `.joblib` is bypassed!
3. `lifespan` in `main.py` unconditionally calls `await asyncio.to_thread(state, "Ahmedabad")`, forcing 540-tree training and TreeSHAP calculations (~15-20s) whenever `app` boots, including in `TestClient`.

MANDATORY CONTEXT:
Read ORIGINAL_REQUEST.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md

YOUR MISSION:
Perform a comprehensive technical investigation and design complete, drop-in blueprints for:
1. Modularizing `backend/app/main.py` (currently 602 lines) into `backend/app/routes/`:
   - `heat.py` (`/api/heat/*`)
   - `models.py` (`/api/models/*`)
   - `simulation.py` (`/api/simulation/*`)
   - `optimization.py` (`/api/optimization/*`)
   - `risk.py` (`/api/risk/*`)
   - `data.py` (`/api/data/*`)
   - `ai.py` (`/api/ai/*`)
   - `reports.py` (`/api/reports/*`)
   - Keep `backend/app/main.py` slim (<120 lines) as an assembly root with CORS, lifespan, exception handlers, and router includes.
2. Lifespan ML model caching & startup optimization:
   - Provide a `PREWARM_STATE=0` (or `FAST_STARTUP=1`) environment variable flag so tests and dev startup can boot in <100ms without blocking.
   - Fix `sample_data()` / `load_or_train()` caching logic so trained models can be reused reliably on disk.
   - Ensure backward compatibility with all existing endpoints and `backend/tests/test_foundation.py` and `test_api.py`.

OUTPUT REQUIREMENTS:
- Working directory: d:\Urban-Heat-Resilience-AI
- State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_1_gen2
- Maintain progress.md with timestamps.
- Write your complete drop-in blueprints and rationale into `analysis.md`.
- Write your final handoff into `handoff.md` following the 5-component protocol: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
- Send a completion message via send_message to the orchestrator (conversation ID: 34ff78fc-de7b-4a98-abfc-54d6c3495098).
- Do NOT edit production code directly (you are read-only).
