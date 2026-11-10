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
