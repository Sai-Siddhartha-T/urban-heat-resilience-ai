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
