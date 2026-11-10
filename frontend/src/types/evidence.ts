import type { City } from "./common";

export type EvidenceKind =
  | "observed"
  | "modelled"
  | "forecast"
  | "predicted"
  | "hypothetical";

export type EvidenceFreshness =
  | "current"
  | "latest_available"
  | "historical"
  | "stale"
  | "unknown";

export interface EvidenceProvenance {
  source: string;
  category: string;
  mode: "live" | "demo";
  kind: EvidenceKind;
  status: string;
  retrieved_at: string;
  observation_time: string | string[] | null;
  city: string | null;
  coverage: string | null;
  resolution: string | null;
  units: Record<string, string>;
  processing: string | null;
  quality: string | null;
  freshness: EvidenceFreshness;
  analysis_ready: boolean;
  limitations: string[];
}

export interface EvidenceAssetSummary {
  id: string;
  city: string | null;
  category: string;
  source: string;
  mode: "live" | "demo";
  analysis_ready: boolean;
  provenance: EvidenceProvenance;
  created_at: string | null;
}

export interface EvidenceAsset extends EvidenceAssetSummary {
  payload: Record<string, unknown>;
}

export interface RasterGrid {
  crs: string;
  transform: [number, number, number, number, number, number];
  shape: [number, number];
  values: (number | null)[][];
  bounds: [number, number, number, number] | null;
}

export interface EvidenceLayer {
  id: string;
  name: string;
  variable: string;
  status: "available" | "unavailable";
  kind: EvidenceKind;
  source: string | null;
  observation_time: string | string[] | null;
  retrieved_at: string | null;
  resolution: string | null;
  unit: string | null;
  asset_id: string | null;
  geojson: Record<string, unknown> | null;
  raster: RasterGrid | null;
  reason: string | null;
  limitations: string[];
}

export interface EvidenceCapability {
  status: "available" | "unavailable" | "partial";
  reason: string | null;
  asset_ids: string[];
}

export interface AnalysisAvailability {
  status: "available" | "unavailable";
  reason: string | null;
  synthetic: boolean;
  dataset_id: string | null;
}

export interface WorkspaceResponse {
  schema_version: "1";
  city: City;
  center: [number, number];
  mode: "normal";
  analysis: AnalysisAvailability;
  assets: EvidenceAssetSummary[];
  layers: EvidenceLayer[];
  capabilities: Record<string, EvidenceCapability>;
  limitations: string[];
}

export interface LayersResponse {
  city: City;
  layers: EvidenceLayer[];
}
