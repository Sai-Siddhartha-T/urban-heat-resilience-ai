import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { isRasterLayer, RASTER_LAYERS } from "../lib/raster";
import { ZoneDetails } from "../components/zone/ZoneDetails";
import type { ZoneProperties } from "../types/geojson";

describe("Map Page SUHII display & Raster Sidecar Linkage", () => {
  const dummyZone: ZoneProperties = {
    id: "AHM_01",
    name: "Sector 01 Central",
    city: "Ahmedabad",
    spatial_block: 0,
    row: 0,
    column: 0,
    area_km2: 1.0,
    ndvi: 0.25,
    ndwi: -0.1,
    ndbi: 0.15,
    ndbai: 0.05,
    building_density: 0.55,
    population_density: 12000,
    population: 12000,
    air_temperature: 38.5,
    humidity: 45,
    rainfall: 0,
    solar_radiation: 650,
    soil_moisture: 0.12,
    land_cover: 1,
    observed_suhii: 4.8,
    predicted_suhii: 4.5,
    predicted_lst: 37.5,
    lst: 37.8,
    rural_reference: 33,
    interval_low: 3.8,
    interval_high: 5.2,
    hotspot: true,
    elderly_share: 0.12,
    available_land_pct: 20,
    roof_pct: 35,
    road_pct: 20,
    protected: false,
    source: "synthetic",
    acquired_at: "2025-05-15",
    risk_score: 42.5,
    hazard: 0.7,
    exposure: 0.6,
    vulnerability: 0.5,
    risk_level: "High",
    missing_indicators: [],
    method: "Risk = H * E * V",
    partition: "test",
    shap: { ndvi: -0.4, building_density: 0.8 },
    shap_base: 3.2,
  };

  it("accurately classifies raster remote sensing layers vs vector/summary attributes", () => {
    // Standard raster remote-sensing and physical continuous surface layers
    expect(isRasterLayer("predicted_suhii")).toBe(true);
    expect(isRasterLayer("ndvi")).toBe(true);
    expect(isRasterLayer("building_density")).toBe(true);
    expect(isRasterLayer("population_density")).toBe(true);
    expect(isRasterLayer("lst")).toBe(true);
    expect(isRasterLayer("ndbi")).toBe(true);
    expect(isRasterLayer("ndwi")).toBe(true);

    // Dynamic raster prefixes
    expect(isRasterLayer("raster_surface_reflectance")).toBe(true);
    expect(isRasterLayer("sentinel_b04_red")).toBe(true);

    // Non-raster discrete/SHAP layers
    expect(isRasterLayer("risk_score")).toBe(false);
    expect(isRasterLayer("shap_ndvi")).toBe(false);
    expect(isRasterLayer("shap_building_density")).toBe(false);
  });

  it("displays predicted SUHII value with proper °C units in ZoneDetails", () => {
    const html = renderToStaticMarkup(<ZoneDetails selected={dummyZone} />);
    // Both predicted SUHII and confidence intervals must have °C units
    expect(html).toContain("Predicted SUHII");
    expect(html).toContain("4.5°C");
    expect(html).toContain("[3.8, 5.2]°C");
  });

  it("renders a sidecar viewer link for raster layers in ZoneDetails", () => {
    const html = renderToStaticMarkup(
      <ZoneDetails selected={dummyZone} layer="predicted_suhii" />
    );
    expect(html).toContain("sidecar://biomolecular_structure_viewer");
    expect(html).toContain("Sidecar Viewer");
    expect(html).toContain('data-testid="zone-sidecar-link"');
  });

  it("renders sidecar link for NDVI raster layer in ZoneDetails", () => {
    const html = renderToStaticMarkup(
      <ZoneDetails selected={dummyZone} layer="ndvi" />
    );
    expect(html).toContain("sidecar://biomolecular_structure_viewer");
    expect(html).toContain('data-testid="zone-sidecar-link"');
  });

  it("does NOT render a sidecar link for non-raster layers in ZoneDetails", () => {
    const html = renderToStaticMarkup(
      <ZoneDetails selected={dummyZone} layer="risk_score" />
    );
    expect(html).not.toContain("sidecar://biomolecular_structure_viewer");
    expect(html).not.toContain('data-testid="zone-sidecar-link"');
  });
});
