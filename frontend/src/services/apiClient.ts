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

function isAnalyticalEndpoint(path: string): boolean {
  const endpoint = path.split(/[?#]/, 1)[0].replace(/\/+$/, "");

  return (
    endpoint === "/api/overview" ||
    endpoint.startsWith("/api/heat/") ||
    endpoint.startsWith("/api/models") ||
    endpoint.startsWith("/api/xai/") ||
    endpoint.startsWith("/api/risk/") ||
    endpoint.startsWith("/api/simulation/") ||
    endpoint === "/api/interventions" ||
    endpoint.startsWith("/api/optimization/") ||
    endpoint.startsWith("/api/ai/") ||
    endpoint.startsWith("/api/reports/")
  );
}

function withDemoMode(url: string): string {
  const hashIndex = url.indexOf("#");
  const urlWithoutHash = hashIndex === -1 ? url : url.slice(0, hashIndex);
  const hash = hashIndex === -1 ? "" : url.slice(hashIndex);
  const queryIndex = urlWithoutHash.indexOf("?");
  const pathname =
    queryIndex === -1 ? urlWithoutHash : urlWithoutHash.slice(0, queryIndex);
  const query = queryIndex === -1 ? "" : urlWithoutHash.slice(queryIndex + 1);
  const params = new URLSearchParams(query);
  params.set("mode", "demo");
  return `${pathname}?${params.toString()}${hash}`;
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
  const demoMode =
    typeof sessionStorage !== "undefined" &&
    sessionStorage.getItem("heatwise-mode") === "demo";

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
    const url =
      path.startsWith("/api/") || path === "/api"
        ? path
        : `/api${path.startsWith("/") ? path : `/${path}`}`;
    const analyticalEndpoint = isAnalyticalEndpoint(url);
    const method = body === undefined ? "GET" : "POST";
    const requestUrl =
      demoMode && analyticalEndpoint && method === "GET"
        ? withDemoMode(url)
        : url;
    const requestBody =
      demoMode &&
      analyticalEndpoint &&
      method === "POST" &&
      body !== null &&
      typeof body === "object" &&
      !Array.isArray(body)
        ? { ...body, mode: "demo" }
        : body;
    try {
      response = await fetch(requestUrl, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...customHeaders,
        },
        ...(body === undefined ? {} : { body: JSON.stringify(requestBody) }),
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
