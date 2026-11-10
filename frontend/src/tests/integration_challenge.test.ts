import { describe, it, expect, vi, beforeEach } from "vitest";
import { PAGE_MAP, DEFAULT_ROUTE, PAGES } from "../lib/constants";
import { request, ApiError } from "../services/apiClient";
import type { RouteState, PageSlug, MapLayer, City, ZoneFeatureCollection, ZoneProperties } from "../types";

// ============================================================================
// 1. URL HASH ROUTING & PARSING CHALLENGE
// ============================================================================

function simulateParseHash(hashString: string): RouteState {
  const raw = hashString.replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const slug = (pathPart || "overview").toLowerCase() as PageSlug;
  const pageDef = PAGE_MAP[slug] || PAGE_MAP[pathPart] || PAGE_MAP.overview;
  const params = new URLSearchParams(queryPart || "");
  const city = (params.get("city") || "Ahmedabad") as City;
  const zoneId = params.get("zone") || "";
  const layer = (params.get("layer") || "predicted_suhii") as MapLayer;
  return {
    page: pageDef.slug,
    city,
    zoneId,
    layer,
  };
}

function simulateNavigate(
  current: RouteState,
  target: string | { page?: string; city?: City; zoneId?: string; layer?: MapLayer },
  params?: Record<string, string>,
): { next: RouteState; hash: string } {
  let next: RouteState;
  if (typeof target === "string") {
    const pageDef = PAGE_MAP[target] || PAGE_MAP[target.toLowerCase()] || PAGE_MAP.overview;
    next = {
      ...current,
      page: pageDef.slug,
      zoneId: params?.zone ?? current.zoneId,
      layer: (params?.layer as MapLayer) ?? current.layer,
    };
  } else {
    const pageDef = target.page
      ? PAGE_MAP[target.page] || PAGE_MAP[target.page.toLowerCase()] || PAGE_MAP.overview
      : null;
    next = {
      page: pageDef ? pageDef.slug : current.page,
      city: target.city ?? current.city,
      zoneId: target.zoneId ?? current.zoneId,
      layer: target.layer ?? current.layer,
    };
  }

  const query = new URLSearchParams();
  if (next.city) query.set("city", next.city);
  if (next.zoneId) query.set("zone", next.zoneId);
  if (next.layer && next.layer !== "predicted_suhii") {
    query.set("layer", next.layer);
  }

  const queryString = query.toString();
  const hash = `#/${next.page}${queryString ? `?${queryString}` : ""}`;
  return { next, hash };
}

describe("Challenge: URL Hash Routing & Query Param Persistence", () => {
  it("routes standard slugs correctly", () => {
    expect(simulateParseHash("#/overview").page).toBe("overview");
    expect(simulateParseHash("#/map").page).toBe("map");
    expect(simulateParseHash("#/compare").page).toBe("compare");
    expect(simulateParseHash("#/prediction").page).toBe("prediction");
    expect(simulateParseHash("#/explain").page).toBe("explain");
    expect(simulateParseHash("#/risk").page).toBe("risk");
    expect(simulateParseHash("#/simulator").page).toBe("simulator");
    expect(simulateParseHash("#/optimizer").page).toBe("optimizer");
    expect(simulateParseHash("#/assistant").page).toBe("assistant");
    expect(simulateParseHash("#/reports").page).toBe("reports");
  });

  it("resolves plural route aliases correctly (e.g., #/predictions and #/simulations)", () => {
    const predResult = simulateParseHash("#/predictions");
    expect(predResult.page).toBe("prediction");
    expect(PAGE_MAP["predictions"]).toBeDefined();

    const simResult = simulateParseHash("#/simulations");
    expect(simResult.page).toBe("simulator");
    expect(PAGE_MAP["simulations"]).toBeDefined();
  });

  it("persists query parameters (city, zone, layer) across tab changes via string target", () => {
    const initial: RouteState = {
      page: "map",
      city: "Delhi",
      zoneId: "DEL_04",
      layer: "ndvi",
    };

    // User navigates from Map to Compare by clicking sidebar ('Zone comparison' or 'compare')
    const { next, hash } = simulateNavigate(initial, "compare");

    expect(next.page).toBe("compare");
    expect(next.city).toBe("Delhi");
    expect(next.zoneId).toBe("DEL_04");
    expect(next.layer).toBe("ndvi");
    expect(hash).toBe("#/compare?city=Delhi&zone=DEL_04&layer=ndvi");
  });

  it("persists city and zone when layer is default (predicted_suhii)", () => {
    const initial: RouteState = {
      page: "map",
      city: "Hyderabad",
      zoneId: "HYD_02",
      layer: "predicted_suhii",
    };

    const { next, hash } = simulateNavigate(initial, "risk");

    expect(next.page).toBe("risk");
    expect(next.city).toBe("Hyderabad");
    expect(next.zoneId).toBe("HYD_02");
    // Default layer is omitted from query string to keep URL clean
    expect(hash).toBe("#/risk?city=Hyderabad&zone=HYD_02");
  });

  it("overrides zone when navigating with params", () => {
    const initial: RouteState = {
      page: "compare",
      city: "Ahmedabad",
      zoneId: "AHM_01",
      layer: "predicted_suhii",
    };

    // User clicks 'Simulate Interventions' for AHM_05 in ZoneComparePage
    const { next, hash } = simulateNavigate(initial, "simulator", { zone: "AHM_05" });

    expect(next.page).toBe("simulator");
    expect(next.zoneId).toBe("AHM_05");
    expect(hash).toBe("#/simulator?city=Ahmedabad&zone=AHM_05");
  });

  it("falls back to overview and default city for unknown slug and empty hash", () => {
    expect(simulateParseHash("").page).toBe("overview");
    expect(simulateParseHash("#/nonexistent").page).toBe("overview");
    expect(simulateParseHash("#/nonexistent").city).toBe("Ahmedabad");
  });
});

// ============================================================================
// 2. STATE INTEGRATION CHALLENGE (App.tsx & Zone Synchronization)
// ============================================================================

describe("Challenge: App.tsx State Synchronization with URL zoneId", () => {
  const mockFeatures = [
    { properties: { id: "AHM_01", name: "Sector 01" } },
    { properties: { id: "AHM_02", name: "Sector 02" } },
    { properties: { id: "AHM_03", name: "Sector 03" } },
  ];

  it("BUG DEMONSTRATION: App.tsx useEffect ignores route.zoneId on initial mount and fallback", () => {
    // In App.tsx:
    // const { page, city, layer, navigate, setCity, setLayer } = useHashRouter();
    // zoneId is NOT destructured from useHashRouter()!
    // And the useEffect only inspects data.data and city:
    // const match = data.data.features.find((f) => f.properties.id === selectedZone?.id);
    // setSelectedZone(match ? match.properties : data.data.features[0].properties);

    const routeZoneIdFromUrl = "AHM_03"; // User entered #/map?city=Ahmedabad&zone=AHM_03
    let selectedZone: { id: string; name: string } | null = null;

    // Simulating App.tsx line 34-39 logic:
    const match = mockFeatures.find((f) => f.properties.id === selectedZone?.id);
    selectedZone = match ? match.properties : mockFeatures[0].properties;

    // Notice: Despite URL having AHM_03, selectedZone defaults to AHM_01 because routeZoneId is never checked!
    expect(selectedZone.id).toBe("AHM_01");
    expect(selectedZone.id).not.toBe(routeZoneIdFromUrl);
  });
});

// ============================================================================
// 3. MULTI-ZONE SELECTION LOGIC IN ZONECOMPAREPAGE
// ============================================================================

describe("Challenge: ZoneComparePage Multi-Zone Selection Logic", () => {
  // Simulating ZoneComparePage toggleZone logic exactly as written in src/pages/ZoneComparePage.tsx:
  function createZoneSelector(initialSelected: string[]) {
    let selectedIds = [...initialSelected];

    const toggleZone = (id: string) => {
      if (selectedIds.includes(id)) {
        if (selectedIds.length > 1) {
          selectedIds = selectedIds.filter((item) => item !== id);
        }
      } else {
        if (selectedIds.length < 4) {
          selectedIds = [...selectedIds, id];
        }
      }
    };

    return {
      getSelected: () => selectedIds,
      toggleZone,
    };
  }

  it("enforces maximum limit of 4 zones", () => {
    const selector = createZoneSelector(["Z1", "Z2", "Z3"]);
    selector.toggleZone("Z4"); // 4th zone -> allowed
    expect(selector.getSelected()).toEqual(["Z1", "Z2", "Z3", "Z4"]);

    selector.toggleZone("Z5"); // 5th zone -> blocked
    expect(selector.getSelected()).toEqual(["Z1", "Z2", "Z3", "Z4"]);
    expect(selector.getSelected().length).toBe(4);
  });

  it("prevents selecting 0 zones by blocking removal of the last remaining zone", () => {
    const selector = createZoneSelector(["Z1", "Z2"]);
    selector.toggleZone("Z2");
    expect(selector.getSelected()).toEqual(["Z1"]);

    selector.toggleZone("Z1"); // Cannot remove last zone
    expect(selector.getSelected()).toEqual(["Z1"]);
    expect(selector.getSelected().length).toBe(1);
  });

  it("BUG DEMONSTRATION: City switch leaves stale zone IDs in selectedIds state", () => {
    // In ZoneComparePage.tsx:
    // const allZones = data?.features?.map(f => f.properties) || [];
    // const defaultSelected = allZones.slice(0, 2).map(z => z.id);
    // const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);
    //
    // useState only initializes ONCE on mount. When city changes from Ahmedabad to Delhi,
    // selectedIds is NOT reset or synchronized with the new city's zones!

    const ahmedabadZones = ["AHM_01", "AHM_02", "AHM_03", "AHM_04"];
    const delhiZones = ["DEL_01", "DEL_02", "DEL_03", "DEL_04"];

    // Component mounted with Ahmedabad
    let selectedIds = ahmedabadZones.slice(0, 2); // ["AHM_01", "AHM_02"]

    // User switches city to Delhi, prop data changes to delhiZones.
    // selectedIds is NOT reset because useState does not re-run on prop change without a useEffect or key!
    const activeDelhiZones = delhiZones.filter((id) => selectedIds.includes(id));

    // Stale Ahmedabad IDs match ZERO Delhi zones!
    expect(activeDelhiZones).toEqual([]);
    expect(activeDelhiZones.length).toBe(0);

    // If user tries to click a Delhi zone (DEL_01), selectedIds already contains 2 stale IDs:
    const toggle = (id: string) => {
      if (selectedIds.includes(id)) {
        if (selectedIds.length > 1) selectedIds = selectedIds.filter((x) => x !== id);
      } else {
        if (selectedIds.length < 4) selectedIds = [...selectedIds, id];
      }
    };

    toggle("DEL_01"); // selectedIds: ["AHM_01", "AHM_02", "DEL_01"] (length 3)
    toggle("DEL_02"); // selectedIds: ["AHM_01", "AHM_02", "DEL_01", "DEL_02"] (length 4)
    toggle("DEL_03"); // BLOCKED! Length is 4, even though only 2 Delhi zones are active!

    expect(selectedIds).toContain("AHM_01");
    expect(selectedIds).toContain("AHM_02");
    expect(selectedIds).not.toContain("DEL_03");
  });

  it("handles empty zone dataset gracefully without throwing in KPI calculations", () => {
    const emptyZones: ZoneProperties[] = [];
    const maxSuhii = emptyZones.length > 0 ? Math.max(...emptyZones.map((z) => z.predicted_suhii)) : 0;
    const minSuhii = emptyZones.length > 0 ? Math.min(...emptyZones.map((z) => z.predicted_suhii)) : 0;
    const suhiiDisparity = (maxSuhii - minSuhii).toFixed(1);

    expect(suhiiDisparity).toBe("0.0");
    expect(emptyZones.reduce((acc, z) => acc + z.population, 0)).toBe(0);
  });
});

// ============================================================================
// 4. API CLIENT ERROR HANDLING CHALLENGE
// ============================================================================

describe("Challenge: API Client Error Handling in apiClient.ts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("handles HTTP 400 Bad Request with JSON detail", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Invalid query parameters" }),
    } as Response);

    try {
      await request("/test");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(400);
      expect(apiErr.message).toBe("Invalid query parameters");
    }
  });

  it("handles HTTP 422 with FastAPI/Pydantic validation error array", async () => {
    const validationErrors = [
      { loc: ["body", "water_limit"], msg: "Input should be greater than 0", type: "greater_than" },
    ];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({ detail: validationErrors }),
    } as Response);

    try {
      await request("/simulation/run", { water_limit: -5 });
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.message).toBe(JSON.stringify(validationErrors));
    }
  });

  it("handles HTTP 500 when response is plain text/HTML (JSON parse failure on error body)", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON at position 0");
      },
    } as unknown as Response);

    try {
      await request("/crash");
      expect.unreachable();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(500);
      expect(apiErr.message).toBe("Internal Server Error");
    }
  });

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
});
