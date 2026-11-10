import type { City } from "./common";
import type { DatasetMetadata, ZoneProperties } from "./geojson";
import type { FeatureImportance, ModelSummary } from "./ml";

export interface OverviewResponse {
  city: City;
  zone_count: number;
  area_km2: number;
  average_suhii: number;
  average_lst: number;
  hotspots: number;
  high_risk_zones: number;
  population_exposed: number;
  metadata: DatasetMetadata;
  model: ModelSummary;
  importance: FeatureImportance[];
  priority_zones: ZoneProperties[];
}

export type CityOverview = OverviewResponse;
