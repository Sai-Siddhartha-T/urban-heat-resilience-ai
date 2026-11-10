## 2026-11-08T21:28:35Z
You are Explorer M1-Iter2-3: ApiClient Error Handling & Network Resilience Specialist.
Working directory: d:\Urban-Heat-Resilience-AI
State folder: d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3

MANDATORY: Read the original request at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan at:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\PROJECT.md
Read the Gate failure details in:
d:\Urban-Heat-Resilience-AI\.agents\teamwork\orchestrator_1\GATE_STATUS.md
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_2\handoff.md
d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_challenger_m1_2\challenge.md

Your tasks for Milestone 1 Iteration 2:
1. Address the API client error handling gap identified by Challenger M1-2:
   - In `frontend/src/services/apiClient.ts`, examine `request<T>()`.
   - Wrap the outer `fetch()` in try/catch to intercept network disconnects / offline / connection refused errors and rethrow as `ApiError(0, "Network error: ...", err)`.
   - Wrap `response.json()` in try/catch to intercept HTML/non-JSON syntax errors (e.g. Vite SPA HTML fallback) and rethrow as `ApiError(response.status, "Malformed JSON response: ...", err)`.
   - Add optional `signal?: AbortSignal` or timeout support to `request<T>()`.
2. Inspect `frontend/src/tests/integration_challenge.test.ts` (created by Challenger M1-2) to ensure the proposed `apiClient.ts` fixes allow all challenge tests to pass cleanly without regressions.
3. Provide precise drop-in code recommendations for the Worker.
4. Write your report to `analysis.md` and complete `handoff.md` in your state folder.
5. Send completion message to orchestrator. Do not modify source code.
