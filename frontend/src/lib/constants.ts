import React from "react";
import {
  Compass,
  Map as MapIcon,
  Cpu,
  HelpCircle,
  AlertTriangle,
  Sliders,
  Sparkles,
  Bot,
  FileText,
  Scale,
  Activity,
} from "lucide-react";
import type { City, MapLayer, PageSlug, RouteState } from "../types";

export const CITIES: Record<City, [number, number]> = {
  Ahmedabad: [23.0225, 72.5714],
  Delhi: [28.6139, 77.209],
  Hyderabad: [17.385, 78.4867],
};

export const DEFAULT_CITY: City = "Ahmedabad";

export const MAP_LAYERS: Array<{ id: MapLayer; label: string; unit?: string }> = [
  { id: "predicted_suhii", label: "Surface heat · SUHII", unit: "°C" },
  { id: "lst", label: "Land Surface Temperature · LST", unit: "°C" },
  { id: "risk_score", label: "Heat risk index", unit: "0-100" },
  { id: "ndvi", label: "Vegetation · NDVI", unit: "[-1, 1]" },
  { id: "building_density", label: "Built-up areas", unit: "%" },
  { id: "population_density", label: "Population density", unit: "per km²" },
  { id: "shap_ndvi", label: "Spatial SHAP · vegetation", unit: "°C" },
  { id: "shap_ndbi", label: "Spatial SHAP · built-up index", unit: "°C" },
  { id: "shap_building_density", label: "Spatial SHAP · buildings", unit: "°C" },
  { id: "air_quality", label: "Air quality stations", unit: "µg/m³" },
  { id: "weather_stations", label: "Weather stations", unit: "°C" },
  { id: "groundwater", label: "Groundwater wells", unit: "mbgl" },
];

export interface PageDefinition {
  slug: PageSlug;
  title: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

// 10 Canonical Views
export const PAGES: PageDefinition[] = [
  { slug: "overview", title: "Overview", icon: Compass },
  { slug: "map", title: "Live Environmental Map", icon: MapIcon },
  { slug: "prediction", title: "Heat Analysis", icon: Cpu },
  { slug: "environmental", title: "Environmental Analysis", icon: Activity },
  { slug: "risk", title: "Heat Risk", icon: AlertTriangle },
  { slug: "explain", title: "Explainable AI", icon: HelpCircle },
  { slug: "simulator", title: "Mitigation Planning", icon: Sliders },
  { slug: "optimizer", title: "Optimization", icon: Sparkles },
  { slug: "assistant", title: "AI Assistant", icon: Bot },
  { slug: "reports", title: "Reports", icon: FileText },
];

// Zone comparison page definition for backwards compatibility & direct routing
export const COMPARE_PAGE: PageDefinition = {
  slug: "compare",
  title: "Zone comparison",
  icon: Scale,
};

export const PAGE_MAP: Record<string, PageDefinition> = {
  // Overview
  overview: PAGES[0],
  Overview: PAGES[0],
  "Overview Command Center": PAGES[0],

  // Live Environmental Map
  map: PAGES[1],
  "Heat map": PAGES[1],
  "Live Environmental Map": PAGES[1],
  Map: PAGES[1],
  maps: PAGES[1],
  Maps: PAGES[1],

  // Heat Analysis / AI Prediction
  prediction: PAGES[2],
  "AI prediction": PAGES[2],
  Prediction: PAGES[2],
  predictions: PAGES[2],
  Predictions: PAGES[2],
  heat: PAGES[2],
  Heat: PAGES[2],
  "Heat Analysis": PAGES[2],
  "heat-analysis": PAGES[2],

  // Environmental Analysis
  environmental: PAGES[3],
  "Environmental Analysis": PAGES[3],
  env: PAGES[3],
  weather: PAGES[3],

  // Heat Risk
  risk: PAGES[4],
  "Heat risk": PAGES[4],
  "Heat Risk & Vulnerability": PAGES[4],
  Risk: PAGES[4],
  risks: PAGES[4],
  Risks: PAGES[4],

  // Explainable AI
  explain: PAGES[5],
  "Explainable AI": PAGES[5],
  Explain: PAGES[5],
  explanation: PAGES[5],
  Explanation: PAGES[5],
  explanations: PAGES[5],
  Explanations: PAGES[5],

  // Mitigation Planning / Intervention simulator
  simulator: PAGES[6],
  "Intervention simulator": PAGES[6],
  "Mitigation Planning": PAGES[6],
  Simulator: PAGES[6],
  simulation: PAGES[6],
  Simulation: PAGES[6],
  simulations: PAGES[6],
  Simulations: PAGES[6],

  // Intervention Optimization
  optimizer: PAGES[7],
  Optimization: PAGES[7],
  Optimizer: PAGES[7],
  "Intervention Optimization": PAGES[7],
  optimize: PAGES[7],
  Optimize: PAGES[7],

  // AI Assistant
  assistant: PAGES[8],
  "AI assistant": PAGES[8],
  "AI Assistant": PAGES[8],
  "AI Climate Assistant": PAGES[8],
  Assistant: PAGES[8],
  assistants: PAGES[8],
  Assistants: PAGES[8],

  // Reports
  reports: PAGES[9],
  Reports: PAGES[9],
  report: PAGES[9],
  Report: PAGES[9],

  // Zone comparison (Backwards-compatible route)
  compare: COMPARE_PAGE,
  "Zone comparison": COMPARE_PAGE,
  ZoneCompare: COMPARE_PAGE,
  comparison: COMPARE_PAGE,
  Comparison: COMPARE_PAGE,
  comparisons: COMPARE_PAGE,
  Comparisons: COMPARE_PAGE,
};

export const DEFAULT_ROUTE: RouteState = {
  page: "overview",
  city: "Ahmedabad",
  zoneId: "",
  layer: "predicted_suhii",
};

export const interventionNames: Record<string, string> = {
  trees: "Urban tree canopy",
  vegetation: "Pocket parks & bioswales",
  parks: "Large public green space",
  cool_roofs: "High-albedo reflective roofs",
  pavements: "Permeable / reflective roads",
  corridors: "Ventilation green corridors",
  roof_gardens: "Rooftop intensive gardens",
  water: "Fountains & retention ponds",
};
