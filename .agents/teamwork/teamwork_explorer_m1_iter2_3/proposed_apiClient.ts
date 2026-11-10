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
