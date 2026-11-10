import type { City, Partition, RiskLevel } from "./common";

export type MLFeatureName =
  | "ndvi"
  | "ndwi"
  | "ndbi"
  | "ndbai"
  | "building_density"
  | "population_density"
  | "air_temperature"
  | "humidity"
  | "rainfall"
  | "solar_radiation"
  | "soil_moisture"
  | "land_cover";

export interface ZoneProperties {
  // Identification & Grid Location
  id: string;
  name: string;
  city: City;
  spatial_block: number;
  row: number;
  column: number;
  area_km2: number;

  // The 12 Machine Learning Feature Predictors
  ndvi: number;               // Normalized Difference Vegetation Index [-1, 1]
  ndwi: number;               // Normalized Difference Water Index [-1, 1]
  ndbi: number;               // Normalized Difference Built-up Index [-1, 1]
  ndbai: number;              // Normalized Difference Bareness Index [-1, 1]
  building_density: number;   // Built fraction [0, 1]
  population_density: number; // Inhabitants per km²
  population: number;         // Total inhabitants in 1 km² cell
  air_temperature: number;    // Ambient temperature (°C)
  humidity: number;           // Relative humidity (%)
  rainfall: number;           // Precipitation (mm)
  solar_radiation: number;    // Solar radiation (W/m²)
  soil_moisture: number;      // Soil volumetric water content (m³/m³)
  land_cover: number;         // Land cover class (0: low built, 1: high built)

  // Surface Heat Metrics (Observed vs. Predicted)
  observed_suhii: number;     // Synthetic ground truth SUHII (°C)
  predicted_suhii: number;    // ML model output (°C)
  predicted_lst: number;      // predicted_suhii + rural_reference (°C)
  lst: number;                // observed_suhii + rural_reference (°C)
  rural_reference: number;    // Configured rural background baseline (°C)
  interval_low: number;       // 90th percentile holdout interval lower bound
  interval_high: number;      // 90th percentile holdout interval upper bound
  hotspot: boolean;           // predicted_suhii >= 4.0 °C

  // Demographics & Physical Land Constraints
  elderly_share: number;      // Fraction of population >= 65 years [0, 1]
  available_land_pct: number; // Ground area available for vegetation/trees [0, 100]
  roof_pct: number;           // Total roof area share [0, 100]
  road_pct: number;           // Total road/pavement area share [0, 100]
  protected: boolean;         // Protected zoning status (prohibits ground interventions)
  source: string;             // Data source identifier ("synthetic" or live provider)
  acquired_at: string;        // ISO timestamp / date string
  socioeconomic_data?: Record<string, unknown> | null;

  // Heat Risk Framework Outputs (Hazard × Exposure × Vulnerability)
  risk_score: number;         // Scaled risk index [0, 100]
  hazard: number;             // Clipped hazard index [0, 1]
  exposure: number;           // Clipped exposure index [0, 1]
  vulnerability: number;      // Clipped vulnerability index [0, 1]
  risk_level: RiskLevel;      // Categorical classification
  missing_indicators: string[]; // Known data limitations
  method: string;             // Mathematical formula documentation

  // ML Tournament & TreeSHAP
  partition: Partition;       // Spatial cross-validation partition
  shap: Record<MLFeatureName | string, number>; // Exact TreeSHAP local additive contributions
  shap_base: number;          // TreeSHAP expected value E[f(x)]
}

export interface GeoJSONPolygon {
  type: "Polygon";
  coordinates: number[][][]; // GeoJSON coordinate rings: [ [ [lon, lat], ... ] ]
}

export interface ZoneFeature {
  type: "Feature";
  geometry: GeoJSONPolygon;
  properties: ZoneProperties;
}

export interface DatasetMetadata {
  source: string;
  synthetic: boolean;
  isSynthetic?: boolean;
  city: City;
  center: [number, number];
  resolution_m: number;
  crs: string;
  acquisition_date: string;
  rural_reference_c: number;
  rural_method: string;
  generated_at: string;
  limitations: string[];
}

export interface ZoneFeatureCollection {
  type: "FeatureCollection";
  features: ZoneFeature[];
  metadata: DatasetMetadata;
}
