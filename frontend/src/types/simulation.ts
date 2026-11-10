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
