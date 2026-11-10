export type City = "Ahmedabad" | "Delhi" | "Hyderabad";

export interface CityCenter {
  name: City;
  center: [number, number]; // [latitude, longitude]
}

export type Partition = "training" | "validation" | "buffer" | "test";

export type RiskLevel = "High" | "Moderate" | "Low";

export type Tone = "green" | "red" | "orange" | "blue" | "mint" | "neutral";

export type MapLayer =
  | "predicted_suhii"
  | "risk_score"
  | "ndvi"
  | "building_density"
  | "population_density"
  | "shap_ndvi"
  | "shap_ndbi"
  | "shap_building_density"
  | "lst"
  | "air_quality"
  | "weather_stations"
  | "groundwater"
  | "land_cover"
  | "exposure"
  | "interventions";

export type TabPage =
  | "Overview"
  | "Map"
  | "Prediction"
  | "Explain"
  | "Risk"
  | "Simulator"
  | "Optimizer"
  | "Assistant"
  | "Reports"
  | "ZoneCompare"
  | "Environmental";

export interface HealthResponse {
  status: "ok";
  database: string;
  synthetic_predictions: boolean;
  analysis_ready: boolean;
  mode: "normal" | "demo";
  schema_revision?: string | null;
}

export interface ApiErrorDetail {
  detail: string | Record<string, unknown>;
}
