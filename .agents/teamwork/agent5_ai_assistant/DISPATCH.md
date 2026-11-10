## 2026-11-10T12:29:48Z
You are specialized AGENT 5: Groq and Gemini Generative AI Engineer working on Milestone M5 (Grounded Multi-Provider AI Climate Assistant) for the Urban Heat Resilience Platform.

Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent5_ai_assistant
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project specification: d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_2\PROJECT.md
Survey findings: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\analysis.md and d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_survey_3\handoff.md

CRITICAL INSTRUCTION:
Read `d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `teamwork_explorer_survey_3\handoff.md` first.
Your exclusive file ownership:
- `backend/app/services/ai.py`
- `backend/app/services/llm/` (all providers, fallback, guardrails, prompts)
- `backend/app/schemas/ai.py`
- `backend/tests/test_ai*.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks (R7):
1. Multi-Provider Fallback Architecture:
   - Ensure resilient provider orchestration: Groq (`GroqProvider`) with fallback to Google Gemini (`GeminiProvider`), handling transient rate limits and network errors with exponential backoff.
2. Fact Grounding & Anti-Hallucination Guardrails:
   - Ground prompts strictly in actual backend context facts (zone LST, weather, air quality, groundwater depth, risk score, interventions).
   - Enforce source citation validation: every assertion must cite valid backend fact IDs.
   - Enforce numeric guardrails: verify numbers cited in prose match actual data within 5% tolerance.
   - Feasibility validation: check suggested cooling interventions via `simulate()` to prevent physically impossible claims.
3. User-Facing Error Reporting on Provider Downtime (CRITICAL R7 Requirement):
   - In `backend/app/services/llm/fallback.py`, when configured external providers fail or credentials are missing, DO NOT return synthetic hallucinated prose.
   - Return structured, user-facing error indicators explaining the provider downtime, accompanied by clear setup documentation (`GROQ_API_KEY` / `GEMINI_API_KEY`).
   - Delineate deterministic analytical summaries from generative responses.
4. Verification:
   - Run `pytest backend/tests/test_ai_service.py backend/tests/test_ai_agent_m5.py`. Ensure all tests pass.
   - Document all changes and test outputs in `handoff.md`.

Write your report to `d:\Urban-Heat-Resilience-AI\.agents\teamwork\agent5_ai_assistant\handoff.md` and send a message when complete.
