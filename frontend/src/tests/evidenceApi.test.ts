import { beforeEach, describe, expect, it, vi } from "vitest";
import { evidenceService } from "../services/evidenceService";
import type {
  EvidenceAsset,
  EvidenceAssetSummary,
  EvidenceLayer,
  EvidenceProvenance,
  LayersResponse,
  WorkspaceResponse,
} from "../types";

const provenance: EvidenceProvenance = {
  source: "Open-Meteo",
  category: "weather",
  mode: "live",
  kind: "observed",
  status: "latest_available",
  retrieved_at: "2026-11-10T10:00:00Z",
  observation_time: "2026-11-10T09:00:00Z",
  city: "Ahmedabad",
  coverage: null,
  resolution: null,
  units: { temperature_2m: "°C" },
  processing: null,
  quality: null,
  freshness: "current",
  analysis_ready: false,
  limitations: ["Not validated for analysis"],
};

const summary: EvidenceAssetSummary = {
  id: "weather-1",
  city: "Ahmedabad",
  category: "weather",
  source: "Open-Meteo",
  mode: "live",
  analysis_ready: false,
  provenance,
  created_at: "2026-11-10T10:00:00Z",
};

const detail: EvidenceAsset = {
  ...summary,
  payload: { temperature_2m: 38.2, synthetic: false },
};

const layer: EvidenceLayer = {
  id: "air-temperature",
  name: "Air temperature",
  variable: "temperature_2m",
  status: "unavailable",
  kind: "observed",
  source: null,
  observation_time: null,
  retrieved_at: null,
  resolution: null,
  unit: "°C",
  asset_id: null,
  geojson: null,
  raster: null,
  reason: "No mappable evidence is available",
  limitations: [],
};

const workspace: WorkspaceResponse = {
  schema_version: "1",
  city: "Ahmedabad",
  center: [23.0225, 72.5714],
  mode: "normal",
  analysis: {
    status: "unavailable",
    reason: "No validated analysis dataset is available",
    synthetic: false,
    dataset_id: null,
  },
  assets: [summary],
  layers: [layer],
  capabilities: {
    heat: {
      status: "unavailable",
      reason: "No analysis-ready evidence",
      asset_ids: [],
    },
  },
  limitations: ["Catalog-only assets are not analysis-ready"],
};

const layersResponse: LayersResponse = {
  city: "Ahmedabad",
  layers: [layer],
};

describe("evidence API client", () => {
  let fetchCalls: string[];

  beforeEach(() => {
    vi.restoreAllMocks();
    fetchCalls = [];
    const responses: unknown[] = [
      workspace,
      [summary],
      detail,
      layersResponse,
    ];
    let responseIndex = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      fetchCalls.push(String(input));
      const body = responses[responseIndex++];
      return { ok: true, json: async () => body } as Response;
    });
  });

  it("uses the exact evidence endpoint paths and URL-encodes query and asset values", async () => {
    await evidenceService.getWorkspace("Ahmedabad");
    await evidenceService.getAssets("Delhi", "air quality & heat");
    await evidenceService.getAssets("Ahmedabad");
    await evidenceService.getAsset("weather/asset 1", "Hyderabad");
    await evidenceService.getLayers("Ahmedabad");

    expect(fetchCalls).toEqual([
      "/api/workspace?city=Ahmedabad",
      "/api/data/assets?city=Delhi&category=air%20quality%20%26%20heat",
      "/api/data/assets?city=Ahmedabad",
      "/api/data/assets/weather%2Fasset%201?city=Hyderabad",
      "/api/data/layers?city=Ahmedabad",
    ]);
  });

  it("returns typed workspace, summary, detail payload, and layer responses", async () => {
    const workspaceResult = await evidenceService.getWorkspace("Ahmedabad");
    const summaries = await evidenceService.getAssets("Delhi");
    const assetDetail = await evidenceService.getAsset("weather-1", "Hyderabad");
    const availableLayers = await evidenceService.getLayers("Ahmedabad");

    expect(workspaceResult).toEqual(workspace);
    expect(summaries).toEqual([summary]);
    expect(summaries[0]).not.toHaveProperty("payload");
    expect(assetDetail).toEqual(detail);
    expect(assetDetail.payload).toEqual({
      temperature_2m: 38.2,
      synthetic: false,
    });
    expect(availableLayers).toEqual(layersResponse);
    expect(availableLayers.layers[0]).toMatchObject({
      status: "unavailable",
      geojson: null,
      raster: null,
      reason: "No mappable evidence is available",
    });
    expect(assetDetail.analysis_ready).toBe(false);
  });
});
