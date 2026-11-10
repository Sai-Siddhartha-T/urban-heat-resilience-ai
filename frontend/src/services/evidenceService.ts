import { request } from "./apiClient";
import type {
  City,
  EvidenceAsset,
  EvidenceAssetSummary,
  LayersResponse,
  WorkspaceResponse,
} from "../types";

function cityQuery(city: City): string {
  return `city=${encodeURIComponent(city)}`;
}

export const evidenceService = {
  getWorkspace(city: City): Promise<WorkspaceResponse> {
    return request<WorkspaceResponse>(`/api/workspace?${cityQuery(city)}`);
  },

  getAssets(city: City, category?: string): Promise<EvidenceAssetSummary[]> {
    const categoryQuery = category !== undefined
      ? `&category=${encodeURIComponent(category)}`
      : "";
    return request<EvidenceAssetSummary[]>(
      `/api/data/assets?${cityQuery(city)}${categoryQuery}`,
    );
  },

  getAsset(assetId: string, city: City): Promise<EvidenceAsset> {
    return request<EvidenceAsset>(
      `/api/data/assets/${encodeURIComponent(assetId)}?${cityQuery(city)}`,
    );
  },

  getLayers(city: City): Promise<LayersResponse> {
    return request<LayersResponse>(`/api/data/layers?${cityQuery(city)}`);
  },
};
