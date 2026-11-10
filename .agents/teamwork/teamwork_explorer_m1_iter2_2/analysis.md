# Analysis & Implementation Design: Shared Domain Utilities & Test Suite Integrity Remediation

**Author:** Explorer M1-Iter2-2 (Shared Domain Utilities & Test Integrity Specialist)  
**Target:** Worker M1 (`teamwork_worker_m1`)  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_iter2_2\`  
**Date:** 2026-11-08  

---

## 1. Executive Summary

During Milestone 1 Iteration 1, Reviewer M1-2 detected a critical **test integrity violation**:
- In `frontend/src/tests/metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts` (18 out of 34 unit tests), the tested functions were defined locally inside the test files rather than imported from production code.
- Consequently, changes or defects in the actual UI components (`ZoneComparePage.tsx`, `ZoneComparisonChart.tsx`, `WeatherTimeSeriesChart.tsx`) could never be detected by the test suite.
- Furthermore, the cooling potential formula `Math.min(3.0, (z.available_land_pct / 10) * 0.35 + (z.roof_pct / 10) * 0.28 + (z.road_pct / 10) * 0.18)` and weather statistics reduction logic were duplicated across multiple components.

This document delivers a complete, production-grade refactoring design that:
1. Extracts all 7 required domain calculation functions into `frontend/src/lib/utils.ts`.
2. Supports dual invocation signatures (domain objects like `ZoneProperties` and primitive numbers) so that components and unit tests operate with zero impedance.
3. Updates `ZoneComparePage.tsx`, `ZoneComparisonChart.tsx`, and `WeatherTimeSeriesChart.tsx` to consume these shared utilities, eliminating code duplication and fixing the ghost zone selection bug on city switch.
4. Refactors `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts` to delete all local function declarations and import production utilities directly.

---

## 2. Audit of Existing Code & Defect Evidence

### 2.1 Test File Integrity Violations

| File | Lines | Local Mockup Declarations | Production Link |
|---|---|---|---|
| `frontend/src/tests/metrics.test.ts` | 4–39 | `calcSuhii`, `classifyRisk`, `calcCoolingPotential`, `validateInterventionCapacity` | **Zero imports** from `src/` |
| `frontend/src/tests/weather.test.ts` | 3–29 | `interface WeatherPoint`, `computeWeatherExtremes` | **Zero imports** from `src/` |
| `frontend/src/tests/zoneCompare.test.ts` | 3–30 | `interface CompareZone`, `updateZoneSelection`, `computeZoneDeltas` | **Zero imports** from `src/` |

### 2.2 Duplicated Logic in Production Code

1. **Cooling Potential Calculation:**
   - `frontend/src/pages/ZoneComparePage.tsx:59-65`:
     ```ts
     const calcCoolingPot = (z: ZoneProperties) =>
       Math.min(3.0, (z.available_land_pct / 10) * 0.35 + (z.roof_pct / 10) * 0.28 + (z.road_pct / 10) * 0.18);
     ```
   - `frontend/src/components/charts/ZoneComparisonChart.tsx:46-52`:
     ```ts
     const pot = Math.min(3.0, (z.available_land_pct / 10) * 0.35 + (z.roof_pct / 10) * 0.28 + (z.road_pct / 10) * 0.18);
     ```
   - `frontend/src/tests/metrics.test.ts:14-17`:
     ```ts
     function calcCoolingPotential(groundPct: number, roofPct: number, roadPct: number): number {
       const theoretical = (groundPct / 10) * 0.35 + (roofPct / 10) * 0.28 + (roadPct / 10) * 0.18;
       return Number(Math.min(3.0, theoretical).toFixed(2));
     }
     ```

2. **Weather Statistics Reduction:**
   - `frontend/src/components/charts/WeatherTimeSeriesChart.tsx:65-77`: manual `.map()`, `.filter()`, and `.reduce()` logic.
   - `frontend/src/tests/weather.test.ts:10-29`: duplicated manual reduction.

3. **Multi-Zone Selection Toggle:**
   - `frontend/src/pages/ZoneComparePage.tsx:36-46`: inline if/else toggling.
   - `frontend/src/tests/zoneCompare.test.ts:13-20`: local duplicate function.

---

## 3. Shared Production Utility Design (`frontend/src/lib/utils.ts`)

The central utility module `frontend/src/lib/utils.ts` should contain all core presentation, thermal, weather, and spatial selection utilities.

### Drop-in Code for `frontend/src/lib/utils.ts`:

```typescript
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
```

---

## 4. Drop-in Component Refactoring

### 4.1 `frontend/src/pages/ZoneComparePage.tsx`

#### Change 1: Update Imports
```typescript
// Before:
import { fmt } from "../lib/utils";

// After:
import {
  fmt,
  calcCoolingPotential,
  updateZoneSelection,
  computeSuhiiDisparity,
} from "../lib/utils";
```

#### Change 2: Add City/Dataset Change Effect (Fix 3) & Refactor `toggleZone`
```typescript
// Replace lines 30-66:
  // Default to the first two zones (or top 2 hotspots)
  const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
  const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);

  // Reset selection when city or dataset changes to prevent ghost selections
  React.useEffect(() => {
    if (allZones.length > 0) {
      setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
    }
  }, [city, data]);

  const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));

  const toggleZone = (id: string) => {
    setSelectedIds((prev) => updateZoneSelection(prev, id, 4));
  };

  const selectTopHotspots = () => {
    const sorted = [...allZones].sort((a, b) => b.predicted_suhii - a.predicted_suhii);
    setSelectedIds(sorted.slice(0, 3).map((z) => z.id));
  };

  const selectExtremeContrast = () => {
    if (allZones.length < 2) return;
    const sorted = [...allZones].sort((a, b) => b.predicted_suhii - a.predicted_suhii);
    setSelectedIds([sorted[0].id, sorted[sorted.length - 1].id]);
  };

  const suhiiDisparity = computeSuhiiDisparity(selectedZones).toFixed(1);
```

#### Change 3: Update KPI Card Max Cooling Potential (Line 137–139)
```tsx
// Before:
<div className="text-2xl font-bold text-emerald-600 mt-1">
  {selectedZones.length > 0 ? Math.max(...selectedZones.map(calcCoolingPot)).toFixed(2) : "0.00"} °C
</div>

// After:
<div className="text-2xl font-bold text-emerald-600 mt-1">
  {selectedZones.length > 0 ? Math.max(...selectedZones.map(calcCoolingPotential)).toFixed(2) : "0.00"} °C
</div>
```

#### Change 4: Update Indicator Table Max Cooling Potential (Line 258–264)
```tsx
// Before:
<tr>
  <td className="p-3 font-medium text-gray-700">Estimated Max Cooling Potential</td>
  {selectedZones.map((z) => (
    <td key={z.id} className="p-3 font-semibold text-emerald-700">
      {calcCoolingPot(z).toFixed(2)} °C
    </td>
  ))}
</tr>

// After:
<tr>
  <td className="p-3 font-medium text-gray-700">Estimated Max Cooling Potential</td>
  {selectedZones.map((z) => (
    <td key={z.id} className="p-3 font-semibold text-emerald-700">
      {calcCoolingPotential(z).toFixed(2)} °C
    </td>
  ))}
</tr>
```

---

### 4.2 `frontend/src/components/charts/ZoneComparisonChart.tsx`

#### Change 1: Update Imports
```typescript
// Replace lines 12-13:
import type { ZoneProperties } from "../../types/geojson";
import { calcCoolingPotential } from "../../lib/utils";
```

#### Change 2: Consume `calcCoolingPotential` in Chart Data
```typescript
// Replace lines 43-55:
    {
      metric: "Cooling Pot. (°C)",
      ...Object.fromEntries(
        zones.map((z) => [z.id, calcCoolingPotential(z)]),
      ),
    },
```

---

### 4.3 `frontend/src/components/charts/WeatherTimeSeriesChart.tsx`

#### Change 1: Update Imports
```typescript
// Add import at line 16:
import { computeWeatherExtremes } from "../../lib/utils";
```

#### Change 2: Consume `computeWeatherExtremes`
```typescript
// Replace lines 65-77:
  const extremes = computeWeatherExtremes(points);
  const maxTemp = extremes.maxTemp !== null ? extremes.maxTemp.toFixed(1) : "—";
  const minTemp = extremes.minTemp !== null ? extremes.minTemp.toFixed(1) : "—";
  const avgHumidity =
    extremes.meanHumidity !== null ? extremes.meanHumidity.toFixed(1) : "—";
```

---

## 5. Drop-in Test Suite Refactoring (Test Integrity Remediation)

### 5.1 `frontend/src/tests/metrics.test.ts`

Replace the entire file with genuine imports and assertions:

```typescript
import { describe, it, expect } from "vitest";
import {
  calcSuhii,
  classifyRisk,
  calcCoolingPotential,
  validateInterventionCapacity,
} from "../lib/utils";
import type { ZoneProperties } from "../types";

describe("Domain Metrics: SUHII Calculation", () => {
  it("calculates positive SUHII when urban LST exceeds rural baseline", () => {
    expect(calcSuhii(42.5, 38.0)).toBe(4.5);
  });

  it("calculates negative SUHII for cool park/water anomalies", () => {
    expect(calcSuhii(36.2, 38.0)).toBe(-1.8);
  });

  it("supports ZoneProperties-like object input", () => {
    const mockZone = { lst: 41.2, rural_reference: 37.0 } as unknown as ZoneProperties;
    expect(calcSuhii(mockZone)).toBe(4.2);
  });
});

describe("Domain Metrics: Risk Classification", () => {
  it("correctly identifies High risk threshold (>= 65)", () => {
    expect(classifyRisk(65.0)).toBe("High");
    expect(classifyRisk(82.4)).toBe("High");
  });

  it("correctly identifies Moderate risk threshold (35 - 64.9)", () => {
    expect(classifyRisk(35.0)).toBe("Moderate");
    expect(classifyRisk(54.2)).toBe("Moderate");
  });

  it("correctly identifies Low risk threshold (< 35)", () => {
    expect(classifyRisk(34.9)).toBe("Low");
    expect(classifyRisk(12.0)).toBe("Low");
  });
});

describe("Domain Metrics: Cooling Potential & Constraints", () => {
  it("calculates theoretical cooling potential from surface quotas", () => {
    // 20% ground (0.7°C) + 30% roof (0.84°C) + 10% road (0.18°C) = 1.72°C
    expect(calcCoolingPotential(20, 30, 10)).toBe(1.72);
  });

  it("caps maximum combined cooling potential at 3.0 °C", () => {
    expect(calcCoolingPotential(60, 50, 40)).toBe(3.0);
  });

  it("calculates cooling potential from zone properties object", () => {
    const mockZone = {
      available_land_pct: 20,
      roof_pct: 30,
      road_pct: 10,
    } as unknown as ZoneProperties;
    expect(calcCoolingPotential(mockZone)).toBe(1.72);
  });

  it("validates intervention constraints within physical boundaries", () => {
    const result = validateInterventionCapacity(
      { trees: 10, parks: 5, cool_roofs: 20 },
      { ground: 20, roof: 25, road: 15 },
    );
    expect(result.valid).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it("flags violations when ground coverage exceeds available quota", () => {
    const result = validateInterventionCapacity(
      { trees: 15, parks: 10 }, // 25% ground
      { ground: 20, roof: 25, road: 15 },
    );
    expect(result.valid).toBe(false);
    expect(result.violations[0]).toContain("Ground interventions");
  });
});
```

---

### 5.2 `frontend/src/tests/weather.test.ts`

Replace the entire file with genuine imports and assertions:

```typescript
import { describe, it, expect } from "vitest";
import { computeWeatherExtremes } from "../lib/utils";
import type { WeatherSeriesPoint } from "../types";

describe("Weather Series Data Processing", () => {
  const samplePoints: WeatherSeriesPoint[] = [
    { date: "2024-05-01", air_temperature_c: 38.2, relative_humidity_pct: 32.0, hours_with_temperature: 24 },
    { date: "2024-05-02", air_temperature_c: 41.5, relative_humidity_pct: 28.5, hours_with_temperature: 24 },
    { date: "2024-05-03", air_temperature_c: 39.8, relative_humidity_pct: 30.0, hours_with_temperature: 24 },
    { date: "2024-05-04", air_temperature_c: 37.0, relative_humidity_pct: null, hours_with_temperature: 24 },
  ];

  it("computes accurate temperature extremes across sampled dates", () => {
    const extremes = computeWeatherExtremes(samplePoints);
    expect(extremes.maxTemp).toBe(41.5);
    expect(extremes.minTemp).toBe(37.0);
    expect(extremes.meanTemp).toBe(39.1);
  });

  it("computes mean humidity while ignoring null records", () => {
    const extremes = computeWeatherExtremes(samplePoints);
    // (32.0 + 28.5 + 30.0) / 3 = 30.166... -> 30.2
    expect(extremes.meanHumidity).toBe(30.2);
  });

  it("handles empty weather series gracefully without throwing", () => {
    const extremes = computeWeatherExtremes([]);
    expect(extremes.maxTemp).toBeNull();
    expect(extremes.meanHumidity).toBeNull();
  });
});
```

---

### 5.3 `frontend/src/tests/zoneCompare.test.ts`

Replace the entire file with genuine imports and assertions:

```typescript
import { describe, it, expect } from "vitest";
import { updateZoneSelection, computeZoneDeltas } from "../lib/utils";
import type { ZoneDeltaInput } from "../lib/utils";

interface CompareZone extends ZoneDeltaInput {
  id: string;
  name: string;
}

describe("Zone Comparison Logic", () => {
  const zones: CompareZone[] = [
    { id: "AHM_01", name: "Sector 01", predicted_suhii: 4.2, ndvi: 0.12, building_density: 0.68, population: 45000, risk_score: 78.5 },
    { id: "AHM_02", name: "Sector 02", predicted_suhii: 1.8, ndvi: 0.35, building_density: 0.30, population: 18000, risk_score: 35.0 },
    { id: "AHM_03", name: "Sector 03", predicted_suhii: 3.5, ndvi: 0.18, building_density: 0.55, population: 32000, risk_score: 62.0 },
    { id: "AHM_04", name: "Sector 04", predicted_suhii: 2.1, ndvi: 0.28, building_density: 0.40, population: 22000, risk_score: 41.5 },
    { id: "AHM_05", name: "Sector 05", predicted_suhii: 4.8, ndvi: 0.08, building_density: 0.75, population: 52000, risk_score: 85.0 },
  ];

  it("adds a zone to selection when below max capacity (4)", () => {
    const current = ["AHM_01", "AHM_02"];
    const updated = updateZoneSelection(current, "AHM_03");
    expect(updated).toEqual(["AHM_01", "AHM_02", "AHM_03"]);
  });

  it("removes an existing zone from selection", () => {
    const current = ["AHM_01", "AHM_02", "AHM_03"];
    const updated = updateZoneSelection(current, "AHM_02");
    expect(updated).toEqual(["AHM_01", "AHM_03"]);
  });

  it("prevents adding more than 4 zones", () => {
    const current = ["AHM_01", "AHM_02", "AHM_03", "AHM_04"];
    const updated = updateZoneSelection(current, "AHM_05");
    expect(updated).toHaveLength(4);
    expect(updated).not.toContain("AHM_05");
  });

  it("prevents deselecting the final zone (minimum 1 zone retained)", () => {
    const current = ["AHM_01"];
    const updated = updateZoneSelection(current, "AHM_01");
    expect(updated).toEqual(["AHM_01"]);
  });

  it("computes accurate metric deltas between two compared zones", () => {
    const deltas = computeZoneDeltas(zones[0], zones[1]);
    expect(deltas.suhii_delta).toBe(2.4); // 4.2 - 1.8
    expect(deltas.ndvi_delta).toBe(-0.23); // 0.12 - 0.35
    expect(deltas.population_delta).toBe(27000); // 45000 - 18000
    expect(deltas.risk_delta).toBe(43.5); // 78.5 - 35.0
  });

  it("sorts zones accurately by heat disparity to highlight extreme hotspots", () => {
    const sorted = [...zones].sort((a, b) => b.predicted_suhii - a.predicted_suhii);
    expect(sorted[0].id).toBe("AHM_05"); // Hottest (4.8 °C)
    expect(sorted[sorted.length - 1].id).toBe("AHM_02"); // Coolest (1.8 °C)
  });
});
```

---

## 6. Verification and Validation Checklist

For Worker M1 and subsequent reviewers:
1. `npm --prefix frontend test`:
   - All 6 test files (`metrics.test.ts`, `weather.test.ts`, `zoneCompare.test.ts`, `integration_challenge.test.ts`, `button.test.tsx`, `api.test.ts`) must pass with 0 failures.
   - Verify that no domain functions are declared locally in the `tests/` directory.
2. `npm --prefix frontend run build`:
   - Production Vite build must complete with exit code 0 (`tsc -b && vite build`) without any TypeScript diagnostics or lint warnings.
3. Code Inspection:
   - Verify `calcCoolingPotential` formula occurs only ONCE in the entire codebase (`src/lib/utils.ts`).
   - Verify `ZoneComparePage.tsx` and `ZoneComparisonChart.tsx` import and invoke `calcCoolingPotential`.
   - Verify `WeatherTimeSeriesChart.tsx` imports and invokes `computeWeatherExtremes`.
