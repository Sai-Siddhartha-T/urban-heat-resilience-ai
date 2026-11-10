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
