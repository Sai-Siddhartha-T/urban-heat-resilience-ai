# Technical Design Specification: Frontend Type System & Typed Service Layer

**Author:** Explorer M1-2 — Frontend Type System & Service Layer Specialist  
**Target Milestone:** Milestone 1 (Frontend Modularization & Enhancement)  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_2`  
**Date:** 2026-11-08  

---

## 1. Executive Summary

This specification provides the comprehensive, strict TypeScript domain model and modular service layer architecture for the **Heatwise** frontend application (`frontend/`). 

The current codebase suffers from:
1. **Pervasive `any` annotations:** `api.ts` defaults to `<T = any>`, and component props across `App.tsx` (14 subcomponents) and `HeatMap.tsx` are explicitly typed as `any`.
2. **Missing domain contracts:** GeoJSON features, TreeSHAP values, CP-SAT optimizer allocations, Open-Meteo weather series, and LLM chat findings lack compile-time interfaces, leading to brittle property access and runtime failure risks.
3. **Monolithic API client:** All HTTP requests are routed through a 55-line untyped `api()` function in `src/api.ts` with no endpoint-specific encapsulation, error typing, or schema validation.

This document provides drop-in ready TypeScript domain models (`src/types/`), a dedicated typed service layer (`src/services/`), exact prop interfaces for all modular components, and an audit detailing how to eliminate every `: any` annotation across the frontend.

---

## 2. Backend Schema Alignment & Contract Inventory

The backend FastAPI implementation (`backend/app/schemas.py`, `backend/app/main.py`, and `backend/app/services/`) defines strict Pydantic v2 schemas (`extra="forbid", allow_inf_nan=False`). The frontend types are designed in 1:1 mathematical and structural correspondence with these backend models:

| Backend Route | HTTP Method | Backend Schema / Service | Frontend Service Function | Return Type Interface |
|---|---|---|---|---|
| `/api/health` | GET | `HealthResponse` | `heatService.getHealth()` | `HealthResponse` |
| `/api/cities` | GET | `CITIES` dict | `heatService.getCities()` | `CityCenter[]` |
| `/api/overview` | GET | `overview()` in `main.py` | `heatService.getOverview(city)` | `OverviewResponse` |
| `/api/heat/map` | GET | `ZoneFeatureCollection` | `heatService.getHeatMap(city)` | `ZoneFeatureCollection` |
| `/api/heat/hotspots` | GET | `[ZoneProperties]` | `heatService.getHotspots(city)` | `ZoneProperties[]` |
| `/api/heat/predict` | POST | `ZoneRequest` -> `PredictionResponse` / `PredictionBatchResponse` | `heatService.predictZone(city, zoneId)` | `PredictionResponse \| PredictionBatchResponse` |
| `/api/models` | GET | `describe(a)` in `ml.py` | `mlService.getModels(city)` | `ModelSummary` |
| `/api/models/train` | POST | `ZoneRequest` -> `describe(a)` | `mlService.trainModels(city)` | `ModelSummary` |
| `/api/xai/explain` | POST | `ExplanationResponse` | `mlService.getExplanation(city, zoneId)` | `TreeSHAPExplanation` |
| `/api/xai/importance` | GET | `[FeatureImportance]` | `mlService.getFeatureImportance(city)` | `FeatureImportance[]` |
| `/api/risk/analyze` | POST | `RiskRequest` -> `analyze_risk()` | `riskService.analyzeRisk(req)` | `RiskAnalysisResponse` |
| `/api/interventions` | GET | `INTERVENTIONS` & `ASSUMPTIONS` | `simulationService.getInterventions()` | `InterventionsMetadataResponse` |
| `/api/simulation/run` | POST | `SimulationRequest` -> `SimulationResponse` | `simulationService.runSimulation(req)` | `SimulationResponse` |
| `/api/simulation/results`| GET | `[SimulationResponse]` | `simulationService.getSimulationHistory(city)` | `SimulationResponse[]` |
| `/api/optimization/run` | POST | `OptimizationRequest` -> `OptimizationResponse` | `optimizationService.runOptimization(req)` | `OptimizationResponse` |
| `/api/optimization/results`| GET| `[OptimizationResponse]` | `optimizationService.getOptimizationHistory(city)` | `OptimizationResponse[]` |
| `/api/data/series` | GET | `weather_series()` in `sources.py` | `weatherService.getWeatherSeries()` | `WeatherDataResponse` |
| `/api/data/status` | GET | `data_status()` in `main.py` | `dataService.getDataStatus()` | `DataStatusResponse` |
| `/api/data/records` | GET | `records(kind)` in `db.py` | `dataService.getDataRecords(kind)` | `DataRecordItem[]` |
| `/api/data/ingest` | POST | `AreaRequest` | `dataService.ingestData(req)` | `DataIngestResponse` |
| `/api/ai/chat` | POST | `ChatRequest` -> `ChatResponse` | `aiService.chat(req)` | `ChatResponse` |
| `/api/reports/generate`| POST | `ZoneRequest` -> report URLs | `reportService.generateReport(city)` | `ReportGenerateResponse` |

---

## 3. Strict Domain Type Definitions (`frontend/src/types/`)

The types are partitioned into specialized modules under `frontend/src/types/`, exported centrally through `src/types/index.ts`.

### 3.1 `src/types/common.ts`
```typescript
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
  | "shap_building_density";

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
  | "Weather"
  | "ZoneCompare";

export interface HealthResponse {
  status: "ok";
  database: string;
  synthetic_predictions: boolean;
}

export interface ApiErrorDetail {
  detail: string | Record<string, unknown>;
}
```

### 3.2 `src/types/geojson.ts`
Defines the 12 ML feature predictors, full zone properties, geometry, and GeoJSON collections.
```typescript
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
  shap: Record<MLFeatureName, number>; // Exact TreeSHAP local additive contributions
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
```

### 3.3 `src/types/ml.ts`
Defines model candidate metrics, tournament winner, and TreeSHAP explainability structures.
```typescript
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
  contributions: Record<MLFeatureName, number>;
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
```

### 3.4 `src/types/simulation.ts`
Defines intervention types, physical constraints, simulation requests, and response metrics.
```typescript
import type { City } from "./common";

export type InterventionType =
  | "trees"
  | "vegetation"
  | "parks"
  | "cool_roofs"
  | "pavements"
  | "corridors"
  | "roof_gardens"
  | "water";

export type InterventionSurface = "ground" | "roof" | "road";

export interface InterventionSpec {
  name: string;
  surface: InterventionSurface;
  cooling_per_10pct: number; // Cooling in °C per 10% coverage
  water_per_pct: number;     // Water consumption in m³/day per 1% coverage per km²
  vegetation: boolean;       // Contributes towards max_vegetation_pct limit
}

export interface PhysicalConstraints {
  ground: number;            // available_land_pct
  roof: number;              // roof_pct
  road: number;              // road_pct
  max_vegetation_pct: number;
  water_limit: number;
  protected: boolean;
}

export interface SimulationRequest {
  city: City;
  zone_id?: string;
  name: string;
  coverage: Partial<Record<InterventionType, number>>;
  water_limit: number;
  max_vegetation_pct: number;
  tree_count?: number;
  roof_treated_pct?: number;
  road_treated_pct?: number;
}

export interface AreaCoverageTotals {
  ground: number;
  roof: number;
  road: number;
}

export interface SimulationResponse {
  id?: number | string;
  zone_id: string;
  name: string;
  city: string;
  coverage: Record<string, number>;
  feasible: boolean;
  violations: string[];
  before_suhii: number;
  after_suhii: number | null;
  estimated_cooling: number | null;
  sensitivity_range: [number, number] | null;
  water_m3_day: number;
  area_coverage?: AreaCoverageTotals;
  conversion_notes?: string[];
  hypothetical: boolean;
  assumptions: string[];
}
```

### 3.5 `src/types/optimization.ts`
Defines multi-zone CP-SAT discrete optimization requests, allocations, and sensitivity alternatives.
```typescript
import type { City } from "./common";
import type { SimulationResponse } from "./simulation";

export interface OptimizationRequest {
  city: City;
  zone_ids?: string[];
  water_limit: number;
  max_vegetation_pct: number;
  land_limit_pct: number;
  min_cooling: number;
}

export interface ZoneAllocation extends SimulationResponse {
  zone_name: string;
  population: number;
  risk_score: number;
}

export interface OptimizationConstraints {
  max_vegetation_pct: number;
  land_limit_pct: number;
  min_mean_cooling: number;
}

export interface SensitivityScenario {
  label: string;
  status: string;
  feasible: boolean;
  selections: ZoneAllocation[];
  water_used: number;
  water_available: number;
  mean_cooling: number;
  population_in_selected_zones: number;
  violations: string[];
  hypothetical: boolean;
  assumptions: string[];
  objective: string;
  explanation: string;
  constraints: OptimizationConstraints;
}

export interface OptimizationResponse {
  id?: number | string;
  city: string;
  status: string;
  feasible: boolean;
  selections: ZoneAllocation[];
  water_used: number;
  water_available: number;
  mean_cooling: number;
  population_in_selected_zones: number;
  violations: string[];
  hypothetical: boolean;
  assumptions: string[];
  objective: string;
  explanation: string;
  constraints: OptimizationConstraints;
  alternative?: SensitivityScenario;
}
```

### 3.6 `src/types/weather.ts`
Defines time-series weather structures for Open-Meteo ERA5-Land and NASA POWER.
```typescript
export interface WeatherSeriesPoint {
  date: string; // ISO date "YYYY-MM-DD"
  air_temperature_c: number | null;
  relative_humidity_pct: number | null;
  hours_with_temperature?: number;
  rainfall_mm?: number | null;
  wind_speed_m_s?: number | null;
  solar_radiation_mj_m2_day?: number | null;
}

export interface WeatherSeries {
  id?: string;
  source: string;
  latitude: number;
  longitude: number;
  synthetic: boolean;
  variable: string;
  points: WeatherSeriesPoint[];
}

export interface WeatherDataResponse {
  series: WeatherSeries[];
}
```

### 3.7 `src/types/risk.ts`
Defines risk weighting parameters and zone risk breakdowns.
```typescript
import type { City, RiskLevel } from "./common";

export interface RiskRequest {
  city: City;
  zone_id?: string;
  hazard_weight: number;      // [0.1, 3.0]
  exposure_weight: number;    // [0.1, 3.0]
  vulnerability_weight: number; // [0.1, 3.0]
}

export interface VulnerabilityBreakdown {
  zone_id: string;
  risk_score: number;
  hazard: number;
  exposure: number;
  vulnerability: number;
  risk_level: RiskLevel;
  missing_indicators: string[];
  method: string;
}

export interface RiskAnalysisResponse {
  city: string;
  weights: [number, number, number];
  zones: VulnerabilityBreakdown[];
}
```

### 3.8 `src/types/chat.ts`
Defines grounded AI assistant structures, citations, and message history.
```typescript
import type { City } from "./common";
import type { InterventionType } from "./simulation";

export type ChatProvider = "auto" | "groq" | "gemini" | "local";

export interface ChatRequest {
  city: City;
  zone_id?: string;
  message: string;
  provider: ChatProvider;
}

export interface AIFinding {
  statement: string;
  fact_ids: string[];
}

export interface AIFailure {
  provider: string;
  reason: string;
}

export interface ChatFacts {
  prediction: {
    suhii_c: number;
    lst_c: number;
    interval: [number, number];
    synthetic: boolean;
  };
  drivers: Record<string, number>;
  risk: {
    risk_score: number;
    hazard: number;
    exposure: number;
    vulnerability: number;
  };
  constraints: {
    available_land_pct: number;
    roof_pct: number;
    road_pct: number;
    protected: boolean;
  };
  model: {
    name: string;
    evaluation: unknown[];
    synthetic: boolean;
  };
  optimization: unknown;
  scenarios: unknown[];
}

export interface ChatResponse {
  summary: string;
  findings: AIFinding[];
  actions: InterventionType[];
  limitations: string[];
  provider: string;
  fallback: boolean;
  facts: ChatFacts;
  failures: AIFailure[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content?: string;
  response?: ChatResponse;
  timestamp: string;
}
```

### 3.9 `src/types/overview.ts`
Defines city-level overview metrics and top priority zone rankings.
```typescript
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
```

### 3.10 `src/types/data.ts`
Defines live external source ingestion parameters, catalog items, and status metadata.
```typescript
import type { City } from "./common";
import type { DatasetMetadata, GeoJSONPolygon } from "./geojson";

export type IngestSource =
  | "sample"
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
  boundary?: GeoJSONPolygon | null;
  source: IngestSource;
  start_date?: string; // "YYYY-MM-DD"
  end_date?: string;   // "YYYY-MM-DD"
  satellite_product?: SatelliteProduct;
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
  availability: string;
}

export interface DataStatusResponse {
  providers: {
    groq: ProviderStatus;
    gemini: ProviderStatus;
  };
  database: string;
  earth_engine_configured: boolean;
  catalog: DatasetCatalogItem[];
  ingestions: IngestionRecordSummary[];
  prediction_data: string;
}

export interface DataRecordItem {
  id: string | number;
  kind?: string;
  source?: string;
  created_at: string;
  data?: unknown;
  metadata?: Record<string, unknown>;
}

export interface SyntheticSampleIngestResponse {
  source: "synthetic";
  zones: number;
  metadata: DatasetMetadata;
}

export type DataIngestResponse =
  | SyntheticSampleIngestResponse
  | Record<string, unknown>;

export interface ReportGenerateResponse {
  id: string;
  download_url: string;
  csv_url: string;
  markdown_url: string;
}
```

### 3.11 `src/types/index.ts`
Central barrel export:
```typescript
export * from "./common";
export * from "./geojson";
export * from "./ml";
export * from "./simulation";
export * from "./optimization";
export * from "./weather";
export * from "./risk";
export * from "./chat";
export * from "./overview";
export * from "./data";
```

---

## 4. Typed Service Layer Architecture (`frontend/src/services/`)

The monolithic `src/api.ts` is refactored into modular, strongly-typed services:

```
frontend/src/services/
├── apiClient.ts           # Core fetch client with ApiError, auth token & generic get/post
├── heatService.ts         # Overview, GeoJSON map, hotspots, zone predictions, cities
├── mlService.ts           # Models describe, train, TreeSHAP explanation, feature importance
├── simulationService.ts   # Interventions spec, simulate runs, scenario history
├── optimizationService.ts # CP-SAT optimization runs, alternative scenarios, history
├── weatherService.ts      # Weather time-series endpoint
├── riskService.ts         # Parametric risk re-analysis
├── aiService.ts           # Grounded assistant chat
├── dataService.ts         # Ingestion status, catalog, records, ingest triggers
├── reportService.ts       # Report generation and blob download handling
└── index.ts               # Service barrel exports
```

### 4.1 `src/services/apiClient.ts`
```typescript
export class ApiError extends Error {
  public status: number;
  public details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export async function request<T>(path: string, body?: unknown): Promise<T> {
  const token = sessionStorage.getItem("heatwise-token");
  const response = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  if (!response.ok) {
    let errorDetail = "Could not reach the server.";
    let rawError: unknown = null;
    try {
      rawError = await response.json();
      if (rawError && typeof rawError === "object" && "detail" in rawError) {
        const detail = (rawError as { detail: unknown }).detail;
        errorDetail = typeof detail === "string" ? detail : JSON.stringify(detail);
      }
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new ApiError(response.status, errorDetail, rawError);
  }

  return response.json() as Promise<T>;
}

// Backwards-compatible typed wrapper for gradual migration
export async function api<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, body);
}
```

### 4.2 `src/services/heatService.ts`
```typescript
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
    return request<HealthResponse>("/health");
  },

  getCities(): Promise<CityCenter[]> {
    return request<CityCenter[]>("/cities");
  },

  getOverview(city: City): Promise<OverviewResponse> {
    return request<OverviewResponse>(`/overview?city=${encodeURIComponent(city)}`);
  },

  getHeatMap(city: City): Promise<ZoneFeatureCollection> {
    return request<ZoneFeatureCollection>(`/heat/map?city=${encodeURIComponent(city)}`);
  },

  getHotspots(city: City): Promise<ZoneProperties[]> {
    return request<ZoneProperties[]>(`/heat/hotspots?city=${encodeURIComponent(city)}`);
  },

  predictZone(
    city: City,
    zoneId?: string,
  ): Promise<PredictionResponse | PredictionBatchResponse> {
    return request<PredictionResponse | PredictionBatchResponse>("/heat/predict", {
      city,
      zone_id: zoneId,
    });
  },
};
```

### 4.3 `src/services/mlService.ts`
```typescript
import { request } from "./apiClient";
import type {
  City,
  FeatureImportance,
  ModelSummary,
  TreeSHAPExplanation,
} from "../types";

export const mlService = {
  getModels(city: City): Promise<ModelSummary> {
    return request<ModelSummary>(`/models?city=${encodeURIComponent(city)}`);
  },

  trainModels(city: City): Promise<ModelSummary> {
    return request<ModelSummary>("/models/train", { city });
  },

  getExplanation(city: City, zoneId: string): Promise<TreeSHAPExplanation> {
    return request<TreeSHAPExplanation>("/xai/explain", {
      city,
      zone_id: zoneId,
    });
  },

  getFeatureImportance(city: City): Promise<FeatureImportance[]> {
    return request<FeatureImportance[]>(`/xai/importance?city=${encodeURIComponent(city)}`);
  },
};
```

### 4.4 `src/services/simulationService.ts`
```typescript
import { request } from "./apiClient";
import type {
  City,
  InterventionSpec,
  InterventionType,
  SimulationRequest,
  SimulationResponse,
} from "../types";

export interface InterventionsMetadataResponse {
  interventions: Record<InterventionType, InterventionSpec>;
  assumptions: string[];
}

export const simulationService = {
  getInterventions(): Promise<InterventionsMetadataResponse> {
    return request<InterventionsMetadataResponse>("/interventions");
  },

  runSimulation(req: SimulationRequest): Promise<SimulationResponse> {
    return request<SimulationResponse>("/simulation/run", req);
  },

  getSimulationHistory(city: City): Promise<SimulationResponse[]> {
    return request<SimulationResponse[]>(
      `/simulation/results?city=${encodeURIComponent(city)}`,
    );
  },
};
```

### 4.5 `src/services/optimizationService.ts`
```typescript
import { request } from "./apiClient";
import type {
  City,
  OptimizationRequest,
  OptimizationResponse,
} from "../types";

export const optimizationService = {
  runOptimization(req: OptimizationRequest): Promise<OptimizationResponse> {
    return request<OptimizationResponse>("/optimization/run", req);
  },

  getOptimizationHistory(city: City): Promise<OptimizationResponse[]> {
    return request<OptimizationResponse[]>(
      `/optimization/results?city=${encodeURIComponent(city)}`,
    );
  },
};
```

### 4.6 `src/services/weatherService.ts`
```typescript
import { request } from "./apiClient";
import type { WeatherDataResponse } from "../types";

export const weatherService = {
  getWeatherSeries(): Promise<WeatherDataResponse> {
    return request<WeatherDataResponse>("/data/series");
  },
};
```

### 4.7 `src/services/riskService.ts`
```typescript
import { request } from "./apiClient";
import type { RiskAnalysisResponse, RiskRequest } from "../types";

export const riskService = {
  analyzeRisk(req: RiskRequest): Promise<RiskAnalysisResponse> {
    return request<RiskAnalysisResponse>("/risk/analyze", req);
  },
};
```

### 4.8 `src/services/aiService.ts`
```typescript
import { request } from "./apiClient";
import type { ChatRequest, ChatResponse } from "../types";

export const aiService = {
  chat(req: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/ai/chat", req);
  },
};
```

### 4.9 `src/services/dataService.ts`
```typescript
import { request } from "./apiClient";
import type {
  DataIngestRequest,
  DataIngestResponse,
  DataRecordItem,
  DataStatusResponse,
} from "../types";

export const dataService = {
  getDataStatus(): Promise<DataStatusResponse> {
    return request<DataStatusResponse>("/data/status");
  },

  getDataRecords(
    kind: "weather" | "osm" | "satellite" | "monitoring" = "satellite",
  ): Promise<DataRecordItem[]> {
    return request<DataRecordItem[]>(`/data/records?kind=${encodeURIComponent(kind)}`);
  },

  ingestData(req: DataIngestRequest): Promise<DataIngestResponse> {
    return request<DataIngestResponse>("/data/ingest", req);
  },
};
```

### 4.10 `src/services/reportService.ts`
```typescript
import { request } from "./apiClient";
import type { City, ReportGenerateResponse } from "../types";

export const reportService = {
  generateReport(city: City): Promise<ReportGenerateResponse> {
    return request<ReportGenerateResponse>("/reports/generate", { city });
  },

  async downloadFile(url: string, filename: string): Promise<void> {
    const token = sessionStorage.getItem("heatwise-token");
    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  },
};
```

### 4.11 `src/services/index.ts`
```typescript
export * from "./apiClient";
export * from "./heatService";
export * from "./mlService";
export * from "./simulationService";
export * from "./optimizationService";
export * from "./weatherService";
export * from "./riskService";
export * from "./aiService";
export * from "./dataService";
export * from "./reportService";
```

---

## 5. Complete Elimination of `any` Annotations

### 5.1 Component Props Inventory & Replacement Table

| File & Location | Current Untyped Code | Strict Replacement Interface | Strict Replacement Definition |
|---|---|---|---|
| `App.tsx:148` | `function Metric({ ... }: any)` | `MetricCardProps` | `{ label: string; value: string \| number; unit?: string; detail: string; icon: React.ComponentType<{ size?: number }>; tone?: Tone }` |
| `App.tsx:165` | `function ZonePicker({ data, selected, onSelect }: any)` | `ZonePickerProps` | `{ data: ZoneFeatureCollection; selected?: ZoneProperties \| null; onSelect: (zone: ZoneProperties) => void }` |
| `App.tsx:545` | `function Overview({ overview: o, data, selected, onSelect, layer, onLayer, navigate }: any)` | `OverviewPageProps` | `{ overview: OverviewResponse; data: ZoneFeatureCollection; selected: ZoneProperties; onSelect: (zone: ZoneProperties) => void; layer: MapLayer; onLayer: (layer: MapLayer) => void; navigate: (page: TabPage) => void; onToggleCompare?: (zone: ZoneProperties) => void; comparisonIds?: string[] }` |
| `App.tsx:720` | `function ZoneTable({ zones, onSelect }: any)` | `ZoneTableProps` | `{ zones: ZoneProperties[]; onSelect: (zone: ZoneProperties) => void; selectedId?: string; comparisonIds?: string[]; onToggleCompare?: (zone: ZoneProperties) => void }` |
| `App.tsx:775` | `function Importance({ data, local = false }: any)` | `ImportanceChartProps` | `{ data: FeatureImportance[]; local?: boolean }` |
| `App.tsx:824` | `function ZoneDetails({ selected: p, navigate }: any)` | `ZoneDetailsProps` | `{ selected: ZoneProperties; navigate: (page: TabPage) => void; onStartSimulation?: (zoneId: string) => void }` |
| `App.tsx:880` | `function Prediction({ city, data, overview, notify }: any)` | `PredictionPageProps` | `{ city: City; data: ZoneFeatureCollection; overview: OverviewResponse; notify: (message: string) => void }` |
| `App.tsx:1020` | `function Explain({ city, data, selected, onSelect, overview }: any)` | `ExplainPageProps` | `{ city: City; data: ZoneFeatureCollection; selected: ZoneProperties; onSelect: (zone: ZoneProperties) => void; overview: OverviewResponse }` |
| `App.tsx:1087` | `function Risk({ city, data, selected, onSelect }: any)` | `RiskPageProps` | `{ city: City; data: ZoneFeatureCollection; selected: ZoneProperties; onSelect: (zone: ZoneProperties) => void }` |
| `App.tsx:1203` | `function Simulator({ city, data, selected, onSelect, notify }: any)` | `SimulatorPageProps` | `{ city: City; data: ZoneFeatureCollection; selected: ZoneProperties; onSelect: (zone: ZoneProperties) => void; notify: (message: string) => void }` |
| `App.tsx:1426` | `function Optimizer({ city, overview, notify }: any)` | `OptimizerPageProps` | `{ city: City; overview: OverviewResponse; notify: (message: string) => void }` |
| `App.tsx:1639` | `function Assistant({ city, data, selected, onSelect }: any)` | `AssistantPageProps` | `{ city: City; data: ZoneFeatureCollection; selected: ZoneProperties; onSelect: (zone: ZoneProperties) => void }` |
| `App.tsx:1786` | `function Reports({ city, overview, status, notify }: any)` | `ReportsPageProps` | `{ city: City; overview: OverviewResponse; status: DataStatusResponse; notify: (message: string) => void }` |
| `App.tsx:1943` | `function DataDialog({ city, close, notify }: any)` | `DataDialogProps` | `{ city: City; close: () => void; notify: (message: string) => void }` |
| `HeatMap.tsx:47-52` | `HeatMap({ data: any, ... onSelect: (p: any) => void })` | `HeatMapProps` | `{ data: ZoneFeatureCollection; layer: MapLayer; onLayer: (layer: MapLayer) => void; selected: string; onSelect: (zone: ZoneProperties) => void; tall?: boolean }` |
| `HeatMap.tsx:71` | `style={(f: any) => ...}` | Leaflet Style Callback | `style={(feature) => { const f = feature as ZoneFeature; ... }}` |

### 5.2 Internal State & Error Narrowing

1. **State variable types:**
   - In `Assistant`:
     - Old: `const [messages, setMessages] = useState<any[]>([]);`
     - New: `const [messages, setMessages] = useState<ChatMessage[]>([]);`
   - In `Reports`:
     - Old: `const [report, setReport] = useState<any>();`
     - New: `const [report, setReport] = useState<ReportGenerateResponse | null>(null);`
   - In `DataDialog`:
     - Old: `const body: any = { ... };`
     - New: `const body: DataIngestRequest = { city, source, ... };`
2. **Error Narrowing (`catch (e)`):**
   - Old: `} catch (e: any) { notify(e.message); }`
   - New:
     ```typescript
     } catch (err: unknown) {
       const message = err instanceof Error ? err.message : "An unexpected error occurred.";
       notify(message);
     }
     ```
3. **Map and Filter Predicates:**
   - Old: `data.features.find((f: any) => f.properties.id === e.target.value)`
   - New: `data.features.find((f: ZoneFeature) => f.properties.id === e.target.value)`
   - Old: `zones.map((p: any, i: number) => ...)`
   - New: `zones.map((p: ZoneProperties) => ...)`
   - Old: `overview.priority_zones.slice(0, 5).map((p: any) => ...)`
   - New: `overview.priority_zones.slice(0, 5).map((p: ZoneProperties) => ...)`

---

## 6. Shared Utilities & Constants

To accompany the type system and service layer:

### 6.1 `src/lib/constants.ts`
```typescript
import type { City, MapLayer, TabPage } from "../types";

export const CITIES: Record<City, [number, number]> = {
  Ahmedabad: [23.0225, 72.5714],
  Delhi: [28.6139, 77.209],
  Hyderabad: [17.385, 78.4867],
};

export const DEFAULT_CITY: City = "Ahmedabad";

export const MAP_LAYERS: Array<{ id: MapLayer; label: string }> = [
  { id: "predicted_suhii", label: "Surface heat · SUHII" },
  { id: "risk_score", label: "Heat risk" },
  { id: "ndvi", label: "Vegetation · NDVI" },
  { id: "building_density", label: "Built-up areas" },
  { id: "population_density", label: "Population density" },
  { id: "shap_ndvi", label: "Spatial SHAP · vegetation" },
  { id: "shap_ndbi", label: "Spatial SHAP · built-up index" },
  { id: "shap_building_density", label: "Spatial SHAP · buildings" },
];

export const PAGES: TabPage[] = [
  "Overview",
  "Map",
  "Prediction",
  "Explain",
  "Risk",
  "Simulator",
  "Optimizer",
  "Assistant",
  "Reports",
  "Weather",
  "ZoneCompare",
];
```

### 6.2 `src/lib/utils.ts`
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { MLFeatureName } from "../types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function fmt(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

const FEATURE_LABELS: Record<string, string> = {
  ndvi: "Vegetation index",
  ndbi: "Built-up index",
  ndwi: "Water index",
  ndbai: "Bare-soil index",
  building_density: "Building density",
  population_density: "Population density",
  air_temperature: "Air temperature",
  humidity: "Relative humidity",
  rainfall: "Rainfall",
  solar_radiation: "Solar radiation",
  soil_moisture: "Soil moisture",
  land_cover: "Land cover",
};

export function label(key: MLFeatureName | string): string {
  return FEATURE_LABELS[key] || key.replaceAll("_", " ");
}
```

---

## 7. Concrete Implementation Recommendations for the Worker

When the Worker agent executes Milestone 1:

1. **Step 1 — Create `frontend/src/types/`:**
   - Create `common.ts`, `geojson.ts`, `ml.ts`, `simulation.ts`, `optimization.ts`, `weather.ts`, `risk.ts`, `chat.ts`, `overview.ts`, `data.ts`, and `index.ts`.
2. **Step 2 — Create `frontend/src/lib/`:**
   - Create `constants.ts` and `utils.ts` (unifying `cn`, `fmt`, `label`).
3. **Step 3 — Create `frontend/src/services/`:**
   - Create `apiClient.ts`, `heatService.ts`, `mlService.ts`, `simulationService.ts`, `optimizationService.ts`, `weatherService.ts`, `riskService.ts`, `aiService.ts`, `dataService.ts`, `reportService.ts`, and `index.ts`.
4. **Step 4 — Update `HeatMap.tsx`:**
   - Apply `HeatMapProps`, eliminate `data: any`, `onSelect: (p: any) => void`, and `(f: any) => ...`.
5. **Step 5 — Extract Pages and Components:**
   - As each page/component is extracted from `App.tsx` into `src/pages/` and `src/components/`, type its props with the interfaces defined in Section 5.
6. **Step 6 — Verify Compilation & Tests:**
   - Run `npx tsc -b` inside `frontend/` to confirm zero type errors.
   - Run `npm run build` to verify clean Vite bundling.
   - Run `npm test` with Vitest suite.
