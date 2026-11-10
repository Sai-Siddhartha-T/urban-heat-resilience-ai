import type { DatasetMetadata, MLFeatureName, ZoneProperties } from "./geojson";

export type ModelCandidate = "Random Forest" | "XGBoost" | "LightGBM";

export interface ModelMetrics {
  r2: number;
  rmse: number;
  mae: number;
}

export interface ModelEvaluation {
  model: ModelCandidate;
  validation: ModelMetrics;
  test: ModelMetrics;
}

export interface SplitSummary {
  training: number;
  validation: number;
  test: number;
  buffer: number;
  method: string;
}

export interface ModelSummary {
  winner: ModelCandidate;
  interval: number;
  evaluations: ModelEvaluation[];
  metadata: DatasetMetadata;
  split: SplitSummary;
  features: MLFeatureName[];
}

export interface FeatureImportance {
  feature: MLFeatureName;
  importance: number;
}

export interface TreeSHAPExplanation {
  zone_id: string;
  prediction: number;
  base_value: number;
  contributions: Record<MLFeatureName | string, number>;
  note: string;
}

export interface PredictionResponse {
  id: string;
  name: string;
  city: string;
  predicted_suhii: number;
  predicted_lst: number;
  interval_low: number;
  interval_high: number;
  source: string;
  shap: Record<string, number>;
}

export interface PredictionBatchResponse {
  predictions: ZoneProperties[];
  model: ModelSummary;
}
