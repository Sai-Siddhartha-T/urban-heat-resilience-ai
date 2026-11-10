# Handoff Report: ApiClient Error Handling & Network Resilience

**Agent:** Explorer M1-Iter2-3: ApiClient Error Handling & Network Resilience Specialist  
**Working Directory:** `d:\Urban-Heat-Resilience-AI`  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3`  
**Parent / Caller ID:** `34ff78fc-de7b-4a98-abfc-54d6c3495098`  
**Date:** 2026-11-08  
**Handoff Type:** Hard (Investigation complete)

---

## 1. Observation

1. **`frontend/src/services/apiClient.ts` Error Handling Gaps:**
   - **Outer fetch lacks try/catch (Lines 15-22):**
     ```typescript
     const response = await fetch("/api" + path, {
       method: body === undefined ? "GET" : "POST",
       headers: {
         "Content-Type": "application/json",
         ...(token ? { Authorization: `Bearer ${token}` } : {}),
       },
       ...(body === undefined ? {} : { body: JSON.stringify(body) }),
     });
     ```
     When the browser is offline or the backend connection is refused, `fetch()` rejects with a raw `TypeError: Failed to fetch`. This escapes unhandled by `ApiError`.
   - **`response.json()` on HTTP 200 lacks try/catch (Line 39):**
     ```typescript
     return response.json() as Promise<T>;
     ```
     When an API route returns HTTP 200 with HTML (e.g. Vite SPA fallback on misconfigured proxy paths) or non-JSON content, `response.json()` throws a raw `SyntaxError: Unexpected token '<'`.
   - **Missing AbortSignal & Timeout (Line 13):**
     `request<T>(path: string, body?: unknown)` accepts only `path` and `body`. In-flight requests cannot be cancelled when components unmount, and long-running STAC or ingestion queries have no client-side timeout guards.

2. **Challenger Tests in `frontend/src/tests/integration_challenge.test.ts` (Lines 347-386):**
   ```typescript
   it("BUG DEMONSTRATION: HTTP 200 with HTML body throws raw SyntaxError instead of ApiError", async () => { ... expect(err).toBeInstanceOf(SyntaxError); expect(err).not.toBeInstanceOf(ApiError); });
   it("BUG DEMONSTRATION: Network fetch rejection throws raw TypeError instead of ApiError", async () => { ... expect(err).toBeInstanceOf(TypeError); expect(err).not.toBeInstanceOf(ApiError); });
   it("OBSERVATION: request() does not take AbortSignal or timeout option", () => { expect(request.length).toBe(2); });
   ```
   Challenger M1-2 adhered to the "Do not modify source code" constraint by asserting the defective behaviors. Consequently, fixing `apiClient.ts` will cause these 3 tests in `integration_challenge.test.ts` to fail unless they are updated to assert the fixed behavior (`expect(err).toBeInstanceOf(ApiError)`).

3. **Current Test & Build Verification:**
   - `npm test` in `frontend/` currently passes all 6 test files (51 tests passed).
   - `npm run build` currently compiles cleanly (`tsc -b && vite build`) with zero errors.

---

## 2. Logic Chain

1. From Observation 1, unhandled network rejections and HTML body parse failures violate the contract that all API transport and communication errors produce typed `ApiError` instances. UI callers relying on `err instanceof ApiError` fail to intercept these errors, leading to unhandled promise rejections and stuck loading spinners.
2. From Observation 1, adding `options?: RequestOptions | AbortSignal` with `signal` and `timeoutMs` provides vital network resilience for heavy STAC/Open-Meteo/Earth Engine requests without breaking any existing two-argument `request(path, body)` or one-argument `request(path)` callers.
3. From Observation 2, because Challenger M1-2's test suite directly imports `request` and `ApiError` and asserts that raw `SyntaxError` and `TypeError` are thrown, changing `apiClient.ts` to throw `ApiError` without updating `integration_challenge.test.ts` will cause Vitest to fail with assertion errors.
4. From Observation 3, the codebase currently builds and tests cleanly, meaning that supplying drop-in replacement files and patches for `apiClient.ts`, `api.ts`, and `integration_challenge.test.ts` will allow the Worker to resolve Gate Issue #5 cleanly with zero regressions.

---

## 3. Caveats

- **Read-Only Investigation:** Per agent constraints, source code was not modified directly. Proposed replacement files and patch files have been staged in the agent state folder (`.agents/teamwork/teamwork_explorer_m1_iter2_3/`).
- **Parallel Iteration 2 Tracks:** Plural route aliases (`predictions`) and `App.tsx` zone selection sync are being investigated in parallel by Explorer 1 and Explorer 2; their corresponding challenge tests in sections 1-3 of `integration_challenge.test.ts` will be harmonized concurrently by Worker M1.

---

## 4. Conclusion

The ApiClient resilience gaps can be cleanly resolved by:
1. Replacing `frontend/src/services/apiClient.ts` with the hardened implementation (`proposed_apiClient.ts` / `proposed_apiClient.patch`) that:
   - Wraps `fetch()` in `try/catch` and throws `ApiError(0, "Network error: " + errMsg, err)`.
   - Wraps `response.json()` in `try/catch` and throws `ApiError(response.status, "Malformed JSON response: " + parseMsg, err)`.
   - Safely returns `undefined` on HTTP 204 No Content.
   - Adds `options?: RequestOptions | AbortSignal` supporting `signal`, `timeoutMs`, and custom `headers`.
2. Updating `frontend/src/api.ts` to accept and pass `options?: RequestOptions | AbortSignal`.
3. Updating Section 4 of `frontend/src/tests/integration_challenge.test.ts` (`proposed_integration_challenge_section4.patch`) so tests assert that `ApiError` is thrown with status 0 for network drops, status 200 for HTML bodies, and verify AbortSignal cancellation.

All replacement files and patches are prepared in:
- `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_apiClient.ts`
- `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_apiClient.patch`
- `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_integration_challenge_section4.patch`
- `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\analysis.md`

---

## 5. Verification Method

To verify the proposed implementation once applied:

1. **Run Vitest Test Suite:**
   ```bash
   cd frontend
   npm test
   ```
   *Expected Output:* 6 test files passed, all tests green (including Section 4 of `integration_challenge.test.ts` and `api.test.ts`), exit code 0.

2. **Run TypeScript Production Build:**
   ```bash
   cd frontend
   npm run build
   ```
   *Expected Output:* `tsc -b && vite build` succeeds with zero errors, exit code 0.
