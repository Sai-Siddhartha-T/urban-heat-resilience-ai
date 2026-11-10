import type { City } from "./common";
import type { DatasetMetadata, GeoJSONPolygon } from "./geojson";

export type IngestSource =
  | "demo"
  | "weather"
  | "osm"
  | "earth_engine"
  | "worldpop"
  | "openaq"
  | "stac"
  | "sentinel_indices"
  | "nasa_power"
  | "copernicus"
  | "ghsl";

export type SatelliteProduct =
  | "landsat"
  | "sentinel"
  | "modis"
  | "worldcover"
  | "srtm";

export interface DataIngestRequest {
  city: City;
  latitude?: number;
  longitude?: number;
  boundary?: GeoJSONPolygon | string | null;
  source: IngestSource | string;
  start_date?: string; // "YYYY-MM-DD"
  end_date?: string;   // "YYYY-MM-DD"
  satellite_product?: SatelliteProduct | string;
  rural_reference?: number;
}

export interface DatasetCatalogItem {
  name: string;
  type: string;
  description: string;
  live_configured: boolean;
  env_keys: string[];
}

export interface IngestionRecordSummary {
  id: string | number;
  source: string;
  created_at: string;
}

export interface ProviderStatus {
  configured: boolean;
  model: string | null;
  availability: "verified" | "failed" | "not_verified";
  latest_request_success: boolean | null;
  last_attempt_at: string | null;
  last_success_at: string | null;
}

export interface DataStatusResponse {
  providers: {
    groq: ProviderStatus;
    gemini: ProviderStatus;
  };
  database: string;
  earth_engine: {
    configured: boolean;
    credentials_configured: boolean;
    latest_success: string | null;
  };
  catalog: DatasetCatalogItem[];
  ingestions: IngestionRecordSummary[];
  prediction_data: string;
  assets: Array<{
    id: string;
    city: string | null;
    category: string;
    source: string;
    mode: "live" | "demo";
    analysis_ready: boolean;
    provenance: Record<string, unknown>;
    created_at: string;
  }>;
}

export type DataStatus = DataStatusResponse;

export interface DataRecordItem {
  id: string | number;
  kind?: string;
  source?: string;
  created_at: string;
  data?: unknown;
  metadata?: Record<string, unknown>;
}

export interface DemoIngestResponse {
  source: "synthetic_demo";
  mode: "demo";
  zones: number;
  metadata: DatasetMetadata;
}

export type DataIngestResponse =
  | DemoIngestResponse
  | Record<string, unknown>;

export interface ReportGenerateResponse {
  id: string;
  download_url: string;
  csv_url: string;
  markdown_url: string;
}

export type ReportResponse = ReportGenerateResponse;
