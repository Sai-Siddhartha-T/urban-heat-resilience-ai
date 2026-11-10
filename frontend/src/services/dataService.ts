import { request } from "./apiClient";
import type {
  City,
  DataIngestRequest,
  DataIngestResponse,
  DataRecordItem,
  DataStatusResponse,
  WeatherDataResponse,
} from "../types";

export const dataService = {
  getDataStatus(): Promise<DataStatusResponse> {
    return request<DataStatusResponse>("/api/data/status");
  },

  getDataRecords(
    kind: "weather" | "osm" | "satellite" | "monitoring" = "satellite",
  ): Promise<DataRecordItem[]> {
    return request<DataRecordItem[]>(`/api/data/records?kind=${encodeURIComponent(kind)}`);
  },

  ingestData(req: DataIngestRequest): Promise<DataIngestResponse> {
    return request<DataIngestResponse>("/api/data/ingest", req);
  },

  getDataSeries(city?: City | string): Promise<WeatherDataResponse> {
    return request<WeatherDataResponse>(`/api/data/series${city ? `?city=${encodeURIComponent(city)}` : ""}`);
  },

  getSeries(city?: City | string): Promise<WeatherDataResponse> {
    return this.getDataSeries(city);
  },
};
