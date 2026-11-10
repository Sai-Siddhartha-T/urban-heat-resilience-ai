# Technical Analysis: ApiClient Error Handling & Network Resilience

**Agent:** Explorer M1-Iter2-3: ApiClient Error Handling & Network Resilience Specialist  
**Working Directory:** `d:\Urban-Heat-Resilience-AI`  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3`  
**Date:** 2026-11-08  
**Parent / Caller:** `34ff78fc-de7b-4a98-abfc-54d6c3495098`

---

## 1. Executive Summary

During Milestone 1 Iteration 1 Gate review, Challenger M1-2 identified three related resilience vulnerabilities in the frontend HTTP client (`frontend/src/services/apiClient.ts`):
1. **Network Disconnect / Offline Unhandled Exceptions**: The outer `fetch("/api" + path, ...)` was not enclosed in a `try/catch` block. Network outages, connection refused errors, or DNS failures reject with `TypeError: Failed to fetch`, escaping as an unhandled raw `TypeError` rather than a standardized, typed `ApiError(0, ...)`.
2. **Malformed JSON / SPA Fallback Syntax Errors**: Line 39 executed `return response.json() as Promise<T>` without error handling on HTTP 200 responses. When a Vite dev server or proxy serves `index.html` (e.g. on misconfigured upstream paths), `response.json()` throws a raw `SyntaxError: Unexpected token '<'`, escaping as an untyped exception.
3. **Missing Cancellation & Timeout Semantics**: The function signature `request<T>(path: string, body?: unknown)` provided no mechanism to cancel in-flight requests (`AbortSignal`) or guard against slow/hanging satellite/STAC requests (`timeoutMs`).

Furthermore, in `frontend/src/tests/integration_challenge.test.ts`, Challenger M1-2 constructed tests that deliberately asserted the *buggy* behavior (`expect(err).toBeInstanceOf(SyntaxError)`, `expect(err).toBeInstanceOf(TypeError)`, `expect(request.length).toBe(2)`) because challengers operate under strict read-only constraints. If the Worker applies the `apiClient.ts` hardening without updating `integration_challenge.test.ts`, the challenge test suite will fail.

This analysis provides the root cause diagnostics, the exact code modifications for `apiClient.ts` and `api.ts`, and the test updates required for `integration_challenge.test.ts`.

---

## 2. Root Cause & Gap Analysis in `apiClient.ts`

### 2.1 Current Implementation Overview
In `frontend/src/services/apiClient.ts`:
```typescript
export class ApiError extends Error {
  public status: number;
  public details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export async function request<T>(path: string, body?: unknown): Promise<T> {
  const token = typeof sessionStorage !== "undefined" ? sessionStorage.getItem("heatwise-token") : null;
  const response = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  if (!response.ok) {
    let errorDetail = "Could not reach the server.";
    let rawError: unknown = null;
    try {
      rawError = await response.json();
      if (rawError && typeof rawError === "object" && "detail" in rawError) {
        const detail = (rawError as { detail: unknown }).detail;
        errorDetail = typeof detail === "string" ? detail : JSON.stringify(detail);
      }
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new ApiError(response.status, errorDetail, rawError);
  }

  return response.json() as Promise<T>;
}
```

### 2.2 Vulnerability Matrix

| Vulnerability | Trigger Scenario | Current Behavior | Required Behavior |
|---|---|---|---|
| **Outer fetch rejection** | Client offline, network drop, DNS failure, ECONNREFUSED | Unhandled `TypeError: Failed to fetch` | Rethrown as `ApiError(0, "Network error: Failed to fetch", err)` |
| **Abort / Cancellation** | User navigates away, component unmounts, abort called | Unhandled `DOMException: The operation was aborted` | Caught and rethrown as `ApiError(0, "Network error: ...", err)` |
| **Malformed JSON on HTTP 200** | Vite SPA HTML fallback (`<!DOCTYPE html>`), proxy 200 HTML, truncated payload | Unhandled `SyntaxError: Unexpected token '<'` | Caught and rethrown as `ApiError(response.status, "Malformed JSON response: ...", err)` |
| **204 No Content** | Endpoint returns 204 with 0 bytes | `response.json()` throws `SyntaxError: Unexpected end of JSON` | Cleanly returns `undefined as unknown as T` |
| **Infinite Hang** | Hanging upstream STAC or Earth Engine ingestion | Request hangs indefinitely | Configurable `timeoutMs` automatically aborts via internal controller |

---

## 3. Analysis of `frontend/src/tests/integration_challenge.test.ts`

### 3.1 Why the Challenge Tests Assert Bugs
Challenger M1-2 had the constraint **"Do not modify source code"**. To prove that defects existed without breaking `npm test` during Milestone 1 Iteration 1, Challenger wrote tests asserting the exact unhandled behavior:

Lines 347-386:
```typescript
  it("BUG DEMONSTRATION: HTTP 200 with HTML body throws raw SyntaxError instead of ApiError", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => {
        throw new SyntaxError("Unexpected token '<', '<!DOCTYPE '... is not valid JSON");
      },
    } as unknown as Response);

    try {
      await request("/misrouted-html");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(SyntaxError);
      expect(err).not.toBeInstanceOf(ApiError);
    }
  });

  it("BUG DEMONSTRATION: Network fetch rejection throws raw TypeError instead of ApiError", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    try {
      await request("/network-drop");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(TypeError);
      expect((err as TypeError).message).toBe("Failed to fetch");
      expect(err).not.toBeInstanceOf(ApiError);
    }
  });

  it("OBSERVATION: request() does not take AbortSignal or timeout option", () => {
    expect(request.length).toBe(2);
  });
```

### 3.2 Regression Risk & Worker Action
When the Worker hardens `apiClient.ts`:
1. `request("/misrouted-html")` will throw `ApiError`, causing `expect(err).toBeInstanceOf(SyntaxError)` and `expect(err).not.toBeInstanceOf(ApiError)` to FAIL.
2. `request("/network-drop")` will throw `ApiError`, causing `expect(err).toBeInstanceOf(TypeError)` and `expect(err).not.toBeInstanceOf(ApiError)` to FAIL.
3. Adding `options?: RequestOptions | AbortSignal` to `request()` may alter `request.length` or obsolete `expect(request.length).toBe(2)`.

Therefore, the Worker **must update** these 3 tests in `frontend/src/tests/integration_challenge.test.ts` to assert the resolved behavior:
- Verify `err` is an instance of `ApiError`.
- Verify `status` is 200 for HTML on 200, and 0 for network fetch drops.
- Verify `message` contains `"Malformed JSON response"` or `"Network error"`.
- Verify `details` retains the original underlying error (`SyntaxError`, `TypeError`, or `DOMException`).
- Add tests verifying active `AbortSignal` and `timeoutMs` execution.

---

## 4. Proposed Implementation Blueprint for Worker

### 4.1 Interface & Signature Design
```typescript
export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  headers?: Record<string, string>;
}

export async function request<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions | AbortSignal,
): Promise<T>
```
Supporting `RequestOptions | AbortSignal` provides dual ergonomic benefits:
- Callers wanting simple abort passing can pass `controller.signal` directly: `request(path, body, controller.signal)`.
- Callers wanting timeout or custom headers can pass an object: `request(path, body, { timeoutMs: 5000 })`.
- Existing callers passing `request(path)` or `request(path, body)` remain 100% compatible.

### 4.2 Full Proposed `frontend/src/services/apiClient.ts`
The complete replacement file is available in this agent's folder at:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_apiClient.ts`

Key mechanics:
```typescript
export class ApiError extends Error {
  public status: number;
  public details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  headers?: Record<string, string>;
}

export async function request<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions | AbortSignal,
): Promise<T> {
  const token =
    typeof sessionStorage !== "undefined"
      ? sessionStorage.getItem("heatwise-token")
      : null;

  // Normalize options & signal
  let signal: AbortSignal | undefined;
  let timeoutMs: number | undefined;
  let customHeaders: Record<string, string> = {};

  if (options instanceof AbortSignal) {
    signal = options;
  } else if (options && typeof options === "object") {
    signal = options.signal;
    timeoutMs = options.timeoutMs;
    if (options.headers) {
      customHeaders = options.headers;
    }
  }

  // Set up timeout via internal AbortController if requested
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let internalController: AbortController | undefined;

  if (timeoutMs && timeoutMs > 0) {
    internalController = new AbortController();
    timeoutId = setTimeout(() => {
      internalController?.abort(
        new Error(`Request timed out after ${timeoutMs}ms`),
      );
    }, timeoutMs);

    if (signal) {
      if (signal.aborted) {
        internalController.abort(signal.reason);
      } else {
        signal.addEventListener(
          "abort",
          () => internalController?.abort(signal?.reason),
          { once: true },
        );
      }
    }
    signal = internalController.signal;
  }

  try {
    let response: Response;
    try {
      response = await fetch("/api" + path, {
        method: body === undefined ? "GET" : "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...customHeaders,
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        ...(signal ? { signal } : {}),
      });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        throw err;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      throw new ApiError(0, `Network error: ${errMsg}`, err);
    }

    if (!response.ok) {
      let errorDetail = "Could not reach the server.";
      let rawError: unknown = null;
      try {
        rawError = await response.json();
        if (rawError && typeof rawError === "object" && "detail" in rawError) {
          const detail = (rawError as { detail: unknown }).detail;
          errorDetail =
            typeof detail === "string" ? detail : JSON.stringify(detail);
        }
      } catch {
        errorDetail = response.statusText || errorDetail;
      }
      throw new ApiError(response.status, errorDetail, rawError);
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    try {
      return (await response.json()) as T;
    } catch (err: unknown) {
      const parseMsg = err instanceof Error ? err.message : String(err);
      throw new ApiError(
        response.status,
        `Malformed JSON response: ${parseMsg}`,
        err,
      );
    }
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

// Typed api wrapper compatible with existing code
export async function api<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions | AbortSignal,
): Promise<T> {
  return request<T>(path, body, options);
}
```

### 4.3 Proposed Updates for `frontend/src/tests/integration_challenge.test.ts`
The replacement patch for Section 4 is at:
`d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_3\proposed_integration_challenge_section4.patch`

Snippet:
```typescript
  it("handles HTTP 200 with HTML body (e.g. Vite SPA fallback) by throwing ApiError with status 200", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => {
        throw new SyntaxError("Unexpected token '<', '<!DOCTYPE '... is not valid JSON");
      },
    } as unknown as Response);

    try {
      await request("/misrouted-html");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(200);
      expect(apiErr.message).toContain("Malformed JSON response");
      expect(apiErr.details).toBeInstanceOf(SyntaxError);
    }
  });

  it("handles network fetch rejection by throwing ApiError with status 0", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    try {
      await request("/network-drop");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(0);
      expect(apiErr.message).toBe("Network error: Failed to fetch");
      expect(apiErr.details).toBeInstanceOf(TypeError);
    }
  });

  it("supports AbortSignal and aborts in-flight request", async () => {
    const controller = new AbortController();
    globalThis.fetch = vi.fn().mockImplementation((_url, init) => {
      expect(init?.signal).toBe(controller.signal);
      return Promise.reject(new DOMException("The operation was aborted.", "AbortError"));
    });

    try {
      await request("/aborted", undefined, { signal: controller.signal });
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(0);
      expect(apiErr.message).toContain("Network error");
    }
  });

  it("supports timeout option automatically aborting slow request", async () => {
    vi.useFakeTimers();
    try {
      globalThis.fetch = vi.fn().mockImplementation((_url, init) => {
        return new Promise((_, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        });
      });

      const promise = request("/slow", undefined, { timeoutMs: 100 });
      vi.advanceTimersByTime(100);

      await expect(promise).rejects.toThrow(ApiError);
    } finally {
      vi.useRealTimers();
    }
  });
```

### 4.4 Harmonization for `frontend/src/api.ts`
```typescript
import { request, RequestOptions } from "./services/apiClient";
import { reportService } from "./services/reportService";
import { fmt as fmtUtil, label as labelUtil } from "./lib/utils";

export async function api<T = any>(
  path: string,
  body?: unknown,
  options?: RequestOptions | AbortSignal,
): Promise<T> {
  return request<T>(path, body, options);
}

export async function download(url: string, name: string): Promise<void> {
  return reportService.downloadFile(url, name);
}

export const fmt = fmtUtil;
export const label = labelUtil;

export * from "./services";
```

---

## 5. Verification Method

Once Worker M1 applies the changes:
1. **Run Vitest Test Suite:**
   ```bash
   cd frontend
   npm test
   ```
   **Expected Outcome:**
   - 6 test files pass.
   - All tests in `src/tests/api.test.ts` pass (including HTTP 404/500/200 checks).
   - All tests in `src/tests/integration_challenge.test.ts` pass, with Section 4 confirming `ApiError(0, ...)` and `ApiError(200, ...)` and AbortSignal support.
   - Exit code: 0.

2. **Run TypeScript Production Build:**
   ```bash
   cd frontend
   npm run build
   ```
   **Expected Outcome:**
   - `tsc -b && vite build` completes with 0 errors.
   - Clean production bundle in `dist/`.
   - Exit code: 0.
