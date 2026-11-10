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
