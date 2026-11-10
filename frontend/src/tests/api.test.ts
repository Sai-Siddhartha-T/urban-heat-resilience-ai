import { describe, it, expect, vi, beforeEach } from "vitest";
import { fmt, label, api } from "../api";

const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(globalThis, "sessionStorage", {
  value: storageMock,
  writable: true,
});

describe("api utilities: fmt()", () => {
  it("formats decimal numbers in Indian locale (en-IN) with 1 decimal default", () => {
    expect(fmt(1234.56, 1)).toBe("1,234.6");
  });

  it("formats integers with 0 decimal places", () => {
    expect(fmt(50000, 0)).toBe("50,000");
  });

  it("formats small decimals with 2 decimal places", () => {
    expect(fmt(0.128, 2)).toBe("0.13");
  });

  it("handles zero correctly", () => {
    expect(fmt(0, 1)).toBe("0.0");
  });

  it("handles null and undefined gracefully", () => {
    expect(fmt(null)).toBe("—");
    expect(fmt(undefined)).toBe("—");
  });
});

describe("api utilities: label()", () => {
  it("maps known spatial feature keys to human readable labels", () => {
    expect(label("ndvi")).toBe("Vegetation index");
    expect(label("ndbi")).toBe("Built-up index");
    expect(label("building_density")).toBe("Building density");
    expect(label("population_density")).toBe("Population density");
    expect(label("air_temperature")).toBe("Air temperature");
  });

  it("falls back to replacing underscores for unknown keys", () => {
    expect(label("surface_temperature")).toBe("surface temperature");
    expect(label("cooling_capacity_pct")).toBe("cooling capacity pct");
  });
});

describe("api HTTP client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("makes a GET request when body is undefined", async () => {
    const mockData = { status: "ok" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await api("/test/endpoint");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/test/endpoint", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    expect(result).toEqual(mockData);
  });

  it("makes a POST request when body is provided", async () => {
    const mockData = { id: 1 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await api("/test/post", { city: "Ahmedabad" });
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/test/post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city: "Ahmedabad" }),
    });
    expect(result).toEqual(mockData);
  });

  it("adds demo mode to analytical GET requests", async () => {
    sessionStorage.setItem("heatwise-mode", "demo");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    await api("/api/overview?city=Delhi");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/overview?city=Delhi&mode=demo",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("adds demo mode to analytical POST JSON without mutating the caller body", async () => {
    sessionStorage.setItem("heatwise-mode", "demo");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);
    const body = { city: "Ahmedabad", options: { detail: true } };

    await api("/api/heat/predict", body);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/heat/predict",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ ...body, mode: "demo" }),
      }),
    );
    expect(body).toEqual({ city: "Ahmedabad", options: { detail: true } });
  });

  it("does not add demo mode to data ingestion or other non-analytical endpoints", async () => {
    sessionStorage.setItem("heatwise-mode", "demo");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    const nonAnalyticalPaths = [
      "/api/data/ingest",
      "/api/workspace",
      "/api/health",
      "/api/cities",
      "/api/tiles/heat",
    ];
    for (const path of nonAnalyticalPaths) {
      await api(path);
    }

    await api("/api/data/ingest", { city: "Ahmedabad" });

    nonAnalyticalPaths.forEach((path, index) => {
      expect(globalThis.fetch).toHaveBeenNthCalledWith(
        index + 1,
        path,
        expect.objectContaining({ method: "GET" }),
      );
    });
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      nonAnalyticalPaths.length + 1,
      "/api/data/ingest",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ city: "Ahmedabad" }),
      }),
    );
  });

  it("attaches Authorization header when session token exists", async () => {
    sessionStorage.setItem("heatwise-token", "token-xyz-123");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    await api("/secure/path");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/secure/path",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-xyz-123",
        }),
      }),
    );
  });

  it("throws an Error when response.ok is false", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Zone not found" }),
    } as Response);

    await expect(api("/invalid")).rejects.toThrow("Zone not found");
  });

  it("normalizes path with leading /api so it is not doubled to /api/api", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    await api("/api/heat/predict", { city: "Ahmedabad" });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/heat/predict",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("handles 204 No Content response gracefully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
    } as unknown as Response);

    const result = await api("/empty");
    expect(result).toBeUndefined();
  });

  it("throws ApiError with status 0 on network failures", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

    await expect(api("/network-fail")).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      message: expect.stringContaining("Network error: Failed to fetch"),
    });
  });

  it("throws ApiError on malformed JSON response body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new Error("Unexpected token < in JSON");
      },
    } as unknown as Response);

    await expect(api("/bad-json")).rejects.toMatchObject({
      name: "ApiError",
      status: 200,
      message: expect.stringContaining("Malformed JSON response"),
    });
  });

  it("propagates structured error details from 400 Bad Request responses", async () => {
    const errorBody = { detail: [{ loc: ["body", "city"], msg: "field required" }] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => errorBody,
    } as unknown as Response);

    await expect(api("/bad-req", {})).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      details: errorBody,
    });
  });
});

describe("Revised Service Endpoint Integrations", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("heatService.predictZone calls /api/heat/predict with proper payload", async () => {
    const { heatService } = await import("../services/heatService");
    const mockPrediction = { id: "AHM_01", predicted_suhii: 4.2 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockPrediction,
    } as unknown as Response);

    const result = await heatService.predictZone("Ahmedabad", "AHM_01");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/heat/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city: "Ahmedabad", zone_id: "AHM_01" }),
    });
    expect(result).toEqual(mockPrediction);
  });

  it("aiService.chat calls revised /api/ai/chat endpoint", async () => {
    const { aiService } = await import("../services/aiService");
    const mockChatResponse = {
      summary: "High urban heat observed.",
      findings: [],
      actions: ["trees"],
      limitations: [],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockChatResponse,
    } as unknown as Response);

    const chatReq = { city: "Delhi" as const, message: "What cool interventions apply?", provider: "auto" as const };
    const result = await aiService.chat(chatReq);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chatReq),
    });
    expect(result).toEqual(mockChatResponse);
  });

  it("optimizationService.runOptimization calls /api/optimization/run without budget fields", async () => {
    const { optimizationService } = await import("../services/optimizationService");
    const mockOptResponse = {
      city: "Ahmedabad",
      status: "OPTIMAL",
      feasible: true,
      selections: [],
      water_used: 800,
      water_available: 1000,
      mean_cooling: 0.8,
      population_in_selected_zones: 40000,
      hypothetical: true,
      assumptions: [],
      objective: "max_cooling",
      explanation: "Optimized",
      constraints: { max_vegetation_pct: 40, land_limit_pct: 100, min_mean_cooling: 0 },
      violations: [],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockOptResponse,
    } as unknown as Response);

    const optReq = {
      city: "Ahmedabad" as const,
      zone_ids: ["AHM_01", "AHM_02"],
      water_limit: 1000,
      max_vegetation_pct: 40,
      land_limit_pct: 100,
      min_cooling: 0.5,
      budget_limit: 50000,      // MUST be stripped
      budget_enforced: true,    // MUST be stripped
    };

    const result = await optimizationService.runOptimization(optReq);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/optimization/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city: "Ahmedabad",
        zone_ids: ["AHM_01", "AHM_02"],
        water_limit: 1000,
        max_vegetation_pct: 40,
        land_limit_pct: 100,
        min_cooling: 0.5,
      }),
    });
    // Ensure request body does not contain budget keys
    const callArgs = (globalThis.fetch as any).mock.calls[0];
    const parsedBody = JSON.parse(callArgs[1].body);
    expect(parsedBody.budget_limit).toBeUndefined();
    expect(parsedBody.budget_enforced).toBeUndefined();
    expect(result).toEqual(mockOptResponse);
  });

  it("dataService.getDataSeries calls revised /api/data/series endpoint", async () => {
    const { dataService } = await import("../services/dataService");
    const mockSeriesResponse = { series: [] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSeriesResponse,
    } as unknown as Response);

    const result = await dataService.getDataSeries();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/data/series", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    expect(result).toEqual(mockSeriesResponse);
  });

  it("weatherService.getWeatherSeries calls revised /api/data/series endpoint", async () => {
    const { weatherService } = await import("../services/weatherService");
    const mockSeriesResponse = { series: [{ id: "1", source: "weather", latitude: 23, longitude: 72, synthetic: true, variable: "temp", points: [] }] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSeriesResponse,
    } as unknown as Response);

    const result = await weatherService.getWeatherSeries();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/data/series", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    expect(result).toEqual(mockSeriesResponse);
  });
});
