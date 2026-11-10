## 2026-11-09T07:00:16Z
[Message] timestamp=2026-11-09T07:00:16Z sender=34ff78fc-de7b-4a98-abfc-54d6c3495098 priority=MESSAGE_PRIORITY_HIGH content=You are E2E Test Suite Writer (Gen 3) for the E2E Testing Track.

MANDATORY CONTEXT:
Read ORIGINAL_REQUEST.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md at: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md

YOUR MISSION:
Design, implement, and verify the comprehensive, opaque-box End-to-End (E2E) testing suite across Tiers 1–4, and publish `TEST_INFRA.md` and `TEST_READY.md`.

REQUIREMENTS:
1. Architecture & Framework:
   - Create `backend/tests/test_e2e_tiers.py`.
   - Use FastAPI `TestClient(app)` or `httpx.ASGITransport` with mock transport / offline fixtures so the entire suite runs 100% offline and fast.
   - Set `os.environ["FAST_STARTUP"] = "1"` and `os.environ["PREWARM_STATE"] = "0"` so app boot does not train models from scratch.
2. 4 Tiers of Testing (Systematic methodology: Category-Partition, BVA, Pairwise, Real-World):
   - **Tier 1 - Feature Coverage**:
     >=5 tests per major feature area:
     * System health & foundation (`/api/health`, `/api/ready`, `/api/meta`, `/api/cities`)
     * Heat metrics & baseline data (`/api/heat/*`)
     * ML training, cross-validation & predictions (`/api/models/*`)
     * TreeSHAP feature importance & explanations (`/api/explain/*` or `/api/models/explain`)
     * Urban heat risk index & vulnerability (`/api/risk/*`)
     * 8 Intervention simulation models (`/api/simulation/*`)
     * OR-Tools CP-SAT multi-zone optimizer (`/api/optimization/*`)
     * AI resilience assistant with guardrails (`/api/ai/*`)
     * Data ingestion & catalogs (`/api/data/*`)
     * Report generation & export (`/api/reports/*`)
   - **Tier 2 - Boundary & Corner Cases**:
     Boundary Value Analysis:
     * Extreme coordinates (-90, 90, -180, 180, out-of-bounds coords).
     * Zero, negative, and extreme budget / intervention amounts.
     * Over-allocation exceeding zone spatial capacity.
     * Empty GeoJSON features or unclosed polygons.
     * Rapid repeated requests and empty payloads.
     * Malformed JSON and type mismatches (HTTP 422 validation).
   - **Tier 3 - Cross-Feature Pairwise Workflows**:
     * Ingestion -> Baseline Heat -> Prediction -> SHAP Explanation -> Risk Assessment.
     * Prediction -> Simulation (8 interventions) -> Optimizer (CP-SAT multi-zone) -> Cost & Budget allocation -> Report Export.
     * AI Assistant querying simulation results with numerical guardrail verification.
   - **Tier 4 - Real-World Municipal Planning Scenarios**:
     * Scenario A: Ahmedabad heatwave crisis — 5 zones, 45°C ambient, optimizing tree canopy and cool roofs under water and budget constraints.
     * Scenario B: Rapid urbanization flood/heat dual-hazard — high density zone with green corridor and permeable pavement interventions.
     * Scenario C: Industrial corridor retrofit with reflective coatings and industrial cooling.
3. Test Execution & Verification:
   - Run `pytest backend/tests/test_e2e_tiers.py` to confirm all tests pass cleanly with exit code 0.
4. Deliverables:
   - Create `TEST_INFRA.md` at project root (`d:\Urban-Heat-Resilience-AI\TEST_INFRA.md`) following the Project Pattern template.
   - Create `TEST_READY.md` at project root (`d:\Urban-Heat-Resilience-AI\TEST_READY.md`) with test runner commands, tier breakdown, count per tier, and feature checklist.
   - Write `handoff.md` in your state folder.
   - Send completion message to orchestrator (conversation ID: 34ff78fc-de7b-4a98-abfc-54d6c3495098).
