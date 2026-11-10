import { request } from "./apiClient";
import type {
  City,
  CityCenter,
  HealthResponse,
  OverviewResponse,
  PredictionBatchResponse,
  PredictionResponse,
  ZoneFeatureCollection,
  ZoneProperties,
} from "../types";

export const heatService = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },

  getCities(): Promise<CityCenter[]> {
    return request<CityCenter[]>("/api/cities");
  },

  getOverview(city: City | string): Promise<OverviewResponse> {
    return request<OverviewResponse>(`/api/overview?city=${encodeURIComponent(city)}`);
  },

  getHeatMap(city: City | string): Promise<ZoneFeatureCollection> {
    return request<ZoneFeatureCollection>(`/api/heat/map?city=${encodeURIComponent(city)}`);
  },

  getHotspots(city: City | string): Promise<ZoneProperties[]> {
    return request<ZoneProperties[]>(`/api/heat/hotspots?city=${encodeURIComponent(city)}`);
  },

  predictZone(
    cityOrRequest: City | string | { city: City | string; zone_id?: string },
    zoneId?: string,
  ): Promise<PredictionResponse | PredictionBatchResponse> {
    const payload =
      typeof cityOrRequest === "string"
        ? { city: cityOrRequest, ...(zoneId ? { zone_id: zoneId } : {}) }
        : cityOrRequest;
    return request<PredictionResponse | PredictionBatchResponse>("/api/heat/predict", payload);
  },
};
