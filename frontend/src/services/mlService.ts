import { request } from "./apiClient";
import type {
  City,
  FeatureImportance,
  ModelSummary,
  TreeSHAPExplanation,
} from "../types";

export const mlService = {
  getModels(city: City | string): Promise<ModelSummary> {
    return request<ModelSummary>(`/api/models?city=${encodeURIComponent(city)}`);
  },

  trainModels(city: City | string): Promise<ModelSummary> {
    return request<ModelSummary>("/api/models/train", { city });
  },

  getExplanation(city: City | string, zoneId: string): Promise<TreeSHAPExplanation> {
    return request<TreeSHAPExplanation>("/api/xai/explain", {
      city,
      zone_id: zoneId,
    });
  },

  getFeatureImportance(city: City | string): Promise<FeatureImportance[]> {
    return request<FeatureImportance[]>(`/api/xai/importance?city=${encodeURIComponent(city)}`);
  },
};
