## 2026-11-09T13:54:29Z
You are AGENT 5: Groq and Gemini Generative AI Engineer (teamwork_worker).
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_ai_m5\
Original request file: d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Urban-Heat-Resilience-AI\.agents\teamwork\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Your exclusive write ownership:
- `backend/app/services/llm/` (create package: `__init__.py`, `provider.py`, `groq.py`, `gemini.py`, `guardrails.py`, `fallback.py`)
- `backend/app/schemas/ai.py` (create dedicated schemas for AI request, findings, and response)
- `backend/app/services/ai.py` (enhance, provide backward-compatible facade re-exporting chat, guardrails, etc.)
- `backend/tests/test_ai_layer.py` (create or update LLM tests)

Tasks:
1. LLM Architecture & Provider Abstraction:
   - Create `backend/app/services/llm/` package with clean provider abstraction.
   - Groq integration: model discovery (`https://api.groq.com/openai/v1/models`), chat completion with `json_object` format, temperature 0.1, retries, timeouts, rate-limit handling.
   - Google Gemini integration: model discovery (`https://generativelanguage.googleapis.com/v1beta/models`), `generateContent` with `responseMimeType: "application/json"`, retries, timeouts, rate-limit handling.
   - Multi-provider fallback: requested provider -> alternative provider -> local deterministic evidence summary fallback.
2. Structured Response Schemas:
   - Define Pydantic v2 schemas in `backend/app/schemas/ai.py` (`ChatRequest`, `AIFinding`, `AIResponse`, `ChatResponse`).
   - Re-export in `backend/app/schemas.py` and `backend/app/services/ai.py` so existing route `backend/app/routes/ai.py` has zero broken imports.
3. Decision-Support Capabilities:
   The assistant must answer:
   - Why is this zone experiencing high heat?
   - Which environmental factors contribute most (citing TreeSHAP)?
   - Which areas should be prioritized?
   - Which cooling interventions are suitable?
   - Why did the optimizer select a particular combination?
   - What happens under alternative scenarios?
   - What are the limitations of the recommendations?
4. CRITICAL — Strict Grounding & Numeric Guardrails:
   - Ground LLMs on ACTUAL outputs from ML, risk, simulation, and optimization.
   - NEVER invent temperatures, SHAP values, population figures, or cooling effects.
   - Enforce regex-based numeric audit (`NUMERIC_MEASUREMENT_PATTERN`) against supplied zone facts. Unsupported numbers must raise ValueError or trigger fallback.
   - Validate recommended action feasibility using `simulate()`.
5. Testing:
   - Write unit and integration tests in `backend/tests/test_ai_layer.py`.
   - Run `pytest` and verify all tests pass with 0 regressions.

Deliverable:
Write a comprehensive handoff report to:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\worker_ai_m5\handoff.md`
including Observation, Logic Chain, Caveats, Conclusion, and Verification Method with exact test execution results.
When done, message the orchestrator.
