## 2026-11-08T22:06:22Z
[Message] timestamp=2026-11-08T22:06:22Z sender=34ff78fc-de7b-4a98-abfc-54d6c3495098 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer M2-2: ML Spatial Clustering, Optimizer Budget & AI Guardrails Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m2_2

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read previous survey findings:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_backend_2\survey_backend.md

Your mission for Milestone 2:
1. Spatial Cross-Validation Clustering Generalization:
   - In `backend/app/services/ml.py`, the spatial split currently hardcodes `spatial_block = x // 3` assuming an 18x18 grid.
   - Design coordinate-based spatial clustering (e.g. spatial KMeans or spatial column blocking based on normalized longitude/latitude or EPSG:6933 projected coordinates) so that arbitrary custom GeoJSON polygon grids ingested via `/api/data/ingest` do not drop partition cell counts below 15 or raise `ValueError`.
2. Financial Budget Constraints in Optimizer:
   - In `backend/app/schemas.py`, add `budget_limit: float | None = None` to `OptimizationRequest` and `budget_used: float | None = None` to `OptimizationResponse`.
   - In `backend/app/services/planning.py`, add CapEx and OpEx cost coefficients to `INTERVENTIONS` (e.g., cool_roofs: $25/m², vegetation: $35/m², trees: $50/m², water: $75/m², pavements: $20/m², corridors: $45/m², roof_gardens: $60/m², parks: $40/m²).
   - In `optimize()`, add the integer budget constraint to the OR-Tools CP-SAT solver whenever `budget_limit` is provided.
3. AI Guardrail Regex Refinement:
   - In `backend/app/services/ai.py`, the numeric guardrail `re.search(r"\d", ...)` indiscriminately bans all digits, triggering local fallback on calendar years (e.g. "2026") or numbered lists (e.g. "1. Plant trees").
   - Refine the regex to specifically target physical measurements and quantitative metrics with physical units (e.g. `\d+(?:\.\d+)?\s*(?:°C|deg|%|m³|m²|km²|W/m²|mm|inhabitants|people|tons)`) while allowing calendar years, numbered items, and citations.
4. Provide complete drop-in blueprints in `analysis.md` and `handoff.md`.
5. Send completion message to orchestrator. Do not modify source code.
