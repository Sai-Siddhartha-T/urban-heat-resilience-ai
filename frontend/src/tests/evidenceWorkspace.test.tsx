import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { EvidenceWorkspaceContent } from "../pages/EvidenceWorkspacePage";
import { WeatherTimeSeriesChart } from "../components/charts/WeatherTimeSeriesChart";
import type {
  EvidenceAsset,
  EvidenceLayer,
  EvidenceProvenance,
  WorkspaceResponse,
} from "../types";

const provenance: EvidenceProvenance = {
  source: "Open-Meteo",
  category: "weather",
  mode: "live",
  kind: "modelled",
  status: "latest_available",
  retrieved_at: "2026-11-10T10:00:00Z",
  observation_time: "2026-11-10T09:00:00Z",
  city: "Ahmedabad",
  coverage: "City",
  resolution: "Hourly",
  units: { temperature_2m: "°C" },
  processing: "Provider archive",
  quality: "Not analysis validated",
  freshness: "current",
  analysis_ready: false,
  limitations: ["Model-derived weather values"],
};

const availableGeoJsonLayer: EvidenceLayer = {
  id: "weather-point",
  name: "Weather point",
  variable: "temperature_2m",
  status: "available",
  kind: "modelled",
  source: "Open-Meteo",
  observation_time: "2026-11-10T09:00:00Z",
  retrieved_at: "2026-11-10T10:00:00Z",
  resolution: "Point",
  unit: "°C",
  asset_id: "weather-1",
  geojson: {
    type: "Feature",
    geometry: { type: "Point", coordinates: [72.5714, 23.0225] },
    properties: { temperature_2m: 39.1 },
  },
  raster: null,
  reason: null,
  limitations: ["Air temperature is not LST"],
};

const availableRasterLayer: EvidenceLayer = {
  ...availableGeoJsonLayer,
  id: "surface-grid",
  name: "Surface grid",
  variable: "surface_value",
  unit: "K",
  geojson: null,
  raster: {
    crs: "EPSG:4326",
    transform: [72, 0.01, 0, 24, 0, -0.01],
    shape: [2, 2],
    values: [[300.25, null], [301, 302.5]],
    bounds: [72, 23.98, 72.02, 24],
  },
  limitations: ["Native grid values"],
};

const unavailableLayer: EvidenceLayer = {
  ...availableGeoJsonLayer,
  id: "lst",
  name: "Land Surface Temperature",
  variable: "lst",
  status: "unavailable",
  source: null,
  asset_id: null,
  geojson: null,
  reason: "No satellite LST raster has been acquired",
  limitations: ["No surface-temperature evidence"],
};

const workspace: WorkspaceResponse = {
  schema_version: "1",
  city: "Ahmedabad",
  center: [23.0225, 72.5714],
  mode: "normal",
  analysis: {
    status: "unavailable",
    reason: "No validated analysis dataset is available",
    synthetic: false,
    dataset_id: null,
  },
  assets: [{
    id: "weather-1",
    city: "Ahmedabad",
    category: "weather",
    source: "Open-Meteo",
    mode: "live",
    analysis_ready: false,
    provenance,
    created_at: "2026-11-10T10:00:00Z",
  }],
  layers: [availableGeoJsonLayer, availableRasterLayer, unavailableLayer],
  capabilities: {},
  limitations: ["Catalog-only assets are not analysis-ready"],
};

function renderWorkspace(selectedAsset?: EvidenceAsset): string {
  return renderToStaticMarkup(
    <EvidenceWorkspaceContent
      workspace={workspace}
      selectedAssetId={selectedAsset?.id}
      selectedAsset={selectedAsset}
      onInspectAsset={vi.fn()}
    />,
  );
}

describe("normal-mode evidence workspace", () => {
  it("clearly reports unavailable analysis and shows genuine asset provenance and layer reasons", () => {
    const html = renderWorkspace();
    expect(html).toContain("Heat analysis unavailable");
    expect(html).toContain("No validated analysis dataset is available");
    expect(html).toContain("Open-Meteo");
    expect(html).toContain("modelled · latest_available");
    expect(html).toContain("Model-derived weather values");
    expect(html).toContain("Inspect payload");
    expect(html).toContain("available");
    expect(html).toContain("unavailable");
    expect(html).toContain("No satellite LST raster has been acquired");
    expect(html).toContain("Atmospheric air temperature is not satellite Land Surface Temperature (LST).");
    expect(html).toContain("&quot;temperature_2m&quot;:39.1");
    expect(html).not.toContain("Acquired payload · weather-1");
    expect(html).not.toContain("&quot;synthetic&quot;:false");
  });

  it("renders acquired point geometry, raster values and affine/CRS caveats without inventing polygons", () => {
    const html = renderWorkspace();
    expect(html).toContain("72.5714");
    expect(html).toContain("23.0225");
    expect(html).toContain("<circle");
    expect(html).not.toContain("<path");
    expect(html).toContain("300.25");
    expect(html).toContain("NoData");
    expect(html).toContain("EPSG:4326");
    expect(html).toContain("[72, 0.01, 0, 24, 0, -0.01]");
    expect(html).toContain("no reprojection or geospatial alignment");
    expect(html).toContain("GeoJSON CRS: not supplied");
  });

  it("shows a real asset payload only when the selected asset detail is provided", () => {
    const detail: EvidenceAsset = {
      ...workspace.assets[0],
      payload: { temperature_2m: 39.1, unit: "°C", synthetic: false },
    };
    const html = renderWorkspace(detail);
    expect(html).toContain("Acquired payload · weather-1");
    expect(html).toContain("&quot;temperature_2m&quot;: 39.1");
    expect(html).toContain("&quot;synthetic&quot;: false");
    expect(html).toContain("aria-expanded=\"true\"");
  });
});

describe("weather chart provenance", () => {
  it("identifies Open-Meteo forecasts and reanalysis as modeled, not direct measurements", () => {
    const html = renderToStaticMarkup(
      <WeatherTimeSeriesChart
        seriesData={{
          series: [{
            id: "meteo",
            source: "Open-Meteo archive API",
            latitude: 23.0225,
            longitude: 72.5714,
            synthetic: false,
            variable: "Air temperature",
            points: [{
              date: "2026-11-10",
              air_temperature_c: 39.1,
              relative_humidity_pct: 35,
            }],
          }],
        }}
      />,
    );
    expect(html).toContain("Open-Meteo values are model-based forecast or reanalysis products");
    expect(html).toContain("not direct physical station measurements");
    expect(html).not.toContain("These records are direct physical measurements");
    expect(html).toContain("Location:");
  });
});
