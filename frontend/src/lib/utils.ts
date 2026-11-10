import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type {
  MLFeatureName,
  RiskLevel,
  ZoneProperties,
  WeatherSeriesPoint,
} from "../types";

// ============================================================================
// 1. UI & FORMATTING UTILITIES
// ============================================================================

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

// ============================================================================
// 2. THERMAL & RISK DOMAIN CALCULATIONS
// ============================================================================

/**
 * Computes Surface Urban Heat Island Intensity (SUHII) in °C.
 * Accepts either:
 *  - A zone properties object (extracts lst / predicted_lst and rural_reference)
 *  - Explicit numeric parameters: (lst, ruralRef)
 */
export function calcSuhii(
  inputOrLst: number | { lst?: number; predicted_lst?: number; rural_reference?: number },
  ruralRef?: number,
): number {
  if (typeof inputOrLst === "number") {
    const baseline = ruralRef ?? 0;
    return Number((inputOrLst - baseline).toFixed(2));
  }
  const lst = inputOrLst.lst ?? inputOrLst.predicted_lst ?? 0;
  const baseline = inputOrLst.rural_reference ?? ruralRef ?? 0;
  return Number((lst - baseline).toFixed(2));
}

/**
 * Categorizes a composite heat risk score [0, 100] into categorical levels.
 * - High: >= 65.0
 * - Moderate: 35.0 - 64.9
 * - Low: < 35.0
 */
export function classifyRisk(score: number): RiskLevel {
  if (score >= 65) return "High";
  if (score >= 35) return "Moderate";
  return "Low";
}

export interface CoolingSurfaceInput {
  available_land_pct?: number;
  roof_pct?: number;
  road_pct?: number;
}

/**
 * Calculates theoretical cooling potential (°C) based on surface quota availability.
 * Formula: (ground / 10) * 0.35 + (roof / 10) * 0.28 + (road / 10) * 0.18, capped at 3.0 °C.
 * Accepts either:
 *  - A ZoneProperties or CoolingSurfaceInput object
 *  - Explicit numeric parameters: (groundPct, roofPct, roadPct)
 */
export function calcCoolingPotential(
  inputOrGround: CoolingSurfaceInput | number,
  roofPct?: number,
  roadPct?: number,
): number {
  let ground = 0;
  let roof = 0;
  let road = 0;

  if (typeof inputOrGround === "number") {
    ground = inputOrGround;
    roof = roofPct ?? 0;
    road = roadPct ?? 0;
  } else if (inputOrGround && typeof inputOrGround === "object") {
    ground = inputOrGround.available_land_pct ?? 0;
    roof = inputOrGround.roof_pct ?? 0;
    road = inputOrGround.road_pct ?? 0;
  }

  const theoretical = (ground / 10) * 0.35 + (roof / 10) * 0.28 + (road / 10) * 0.18;
  return Number(Math.min(3.0, theoretical).toFixed(2));
}

// ============================================================================
// 3. INTERVENTION CAPACITY VALIDATION
// ============================================================================

export interface InterventionConstraints {
  ground: number;
  roof: number;
  road: number;
}

export interface InterventionCapacityResult {
  valid: boolean;
  violations: string[];
}

/**
 * Validates that requested intervention surface coverage percentages do not exceed
 * physical land/roof/road capacities.
 * Accepts either an InterventionConstraints object or a ZoneProperties object.
 */
export function validateInterventionCapacity(
  coverage: Record<string, number>,
  constraintsOrZone:
    | InterventionConstraints
    | { available_land_pct?: number; roof_pct?: number; road_pct?: number },
): InterventionCapacityResult {
  const constraints: InterventionConstraints =
    "ground" in constraintsOrZone
      ? constraintsOrZone
      : {
          ground: constraintsOrZone.available_land_pct ?? 0,
          roof: constraintsOrZone.roof_pct ?? 0,
          road: constraintsOrZone.road_pct ?? 0,
        };

  const violations: string[] = [];
  const groundUsed = (coverage.trees || 0) + (coverage.parks || 0) + (coverage.corridors || 0);
  const roofUsed = (coverage.cool_roofs || 0) + (coverage.roof_gardens || 0);
  const roadUsed = coverage.pavements || 0;

  if (groundUsed > constraints.ground) {
    violations.push(
      `Ground interventions (${groundUsed}%) exceed available land (${constraints.ground}%).`,
    );
  }
  if (roofUsed > constraints.roof) {
    violations.push(
      `Roof interventions (${roofUsed}%) exceed available roofs (${constraints.roof}%).`,
    );
  }
  if (roadUsed > constraints.road) {
    violations.push(
      `Pavements (${roadUsed}%) exceed available roads (${constraints.road}%).`,
    );
  }

  return { valid: violations.length === 0, violations };
}

// ============================================================================
// 4. METEOROLOGICAL SERIES ANALYSIS
// ============================================================================

export interface WeatherPointInput {
  air_temperature_c?: number | null;
  relative_humidity_pct?: number | null;
}

export interface WeatherExtremes {
  maxTemp: number | null;
  minTemp: number | null;
  meanTemp: number | null;
  meanHumidity: number | null;
}

/**
 * Computes descriptive statistical extremes across a series of meteorological observations.
 * Handles null/undefined records gracefully and rounds results to 1 decimal place.
 */
export function computeWeatherExtremes(
  points: WeatherPointInput[],
): WeatherExtremes {
  const temps = points
    .map((p) => p.air_temperature_c)
    .filter((t): t is number => typeof t === "number" && Number.isFinite(t));
  const humidities = points
    .map((p) => p.relative_humidity_pct)
    .filter((h): h is number => typeof h === "number" && Number.isFinite(h));

  if (temps.length === 0) {
    return { maxTemp: null, minTemp: null, meanTemp: null, meanHumidity: null };
  }

  const maxTemp = Math.max(...temps);
  const minTemp = Math.min(...temps);
  const meanTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
  const meanHumidity =
    humidities.length > 0
      ? humidities.reduce((a, b) => a + b, 0) / humidities.length
      : null;

  return {
    maxTemp: Number(maxTemp.toFixed(1)),
    minTemp: Number(minTemp.toFixed(1)),
    meanTemp: Number(meanTemp.toFixed(1)),
    meanHumidity: meanHumidity !== null ? Number(meanHumidity.toFixed(1)) : null,
  };
}

// ============================================================================
// 5. ZONE SELECTION & DIFFERENTIAL ANALYSIS
// ============================================================================

/**
 * Toggles a zone ID in an active selection list, enforcing a minimum of 1 selection
 * and a configurable maximum capacity (default 4).
 */
export function updateZoneSelection(
  currentIds: string[],
  targetId: string,
  maxSelection = 4,
): string[] {
  if (currentIds.includes(targetId)) {
    if (currentIds.length <= 1) return currentIds; // Retain at least 1 zone
    return currentIds.filter((id) => id !== targetId);
  }
  if (currentIds.length >= maxSelection) return currentIds; // Enforce max limit
  return [...currentIds, targetId];
}

export interface ZoneDeltaInput {
  predicted_suhii: number;
  ndvi: number;
  building_density: number;
  population: number;
  risk_score: number;
}

export interface ZoneDeltas {
  suhii_delta: number;
  ndvi_delta: number;
  building_density_delta: number;
  population_delta: number;
  risk_delta: number;
}

/**
 * Calculates comparative indicator differentials between two zones (zoneA - zoneB).
 */
export function computeZoneDeltas(
  zoneA: ZoneDeltaInput,
  zoneB: ZoneDeltaInput,
): ZoneDeltas {
  return {
    suhii_delta: Number((zoneA.predicted_suhii - zoneB.predicted_suhii).toFixed(2)),
    ndvi_delta: Number((zoneA.ndvi - zoneB.ndvi).toFixed(3)),
    building_density_delta: Number(
      (zoneA.building_density - zoneB.building_density).toFixed(3),
    ),
    population_delta: zoneA.population - zoneB.population,
    risk_delta: Number((zoneA.risk_score - zoneB.risk_score).toFixed(1)),
  };
}

/**
 * Computes thermal disparity (max SUHII - min SUHII) across selected zones.
 */
export function computeSuhiiDisparity(
  zones: Array<{ predicted_suhii: number }>,
): number {
  if (zones.length === 0) return 0;
  const suhiis = zones.map((z) => z.predicted_suhii);
  return Number((Math.max(...suhiis) - Math.min(...suhiis)).toFixed(1));
}
