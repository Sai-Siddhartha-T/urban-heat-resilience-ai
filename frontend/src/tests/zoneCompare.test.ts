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
