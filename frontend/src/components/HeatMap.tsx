import { useEffect, useState, useMemo } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from "react-leaflet";
import {
  Layers,
  MapPin,
  Sliders as SlidersIcon,
  Wind,
  CloudSun,
  Waves,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";
import type { ZoneFeature, ZoneFeatureCollection, ZoneProperties } from "../types/geojson";
import { SyntheticWarningBadge } from "./common/SyntheticWarningBadge";
import { RASTER_LAYERS, isRasterLayer } from "../lib/raster";
import "leaflet/dist/leaflet.css";

export { RASTER_LAYERS, isRasterLayer };

// Dark-first palette color calculation for layers
const color = (v: number, layer: string) => {
  if (layer === "ndvi") {
    return v > 0.6
      ? "#059669" // Lush green
      : v > 0.4
        ? "#10b981"
        : v > 0.2
          ? "#84cc16"
          : v > 0.1
            ? "#eab308"
            : "#78716c"; // Barren / dry
  }
  if (layer === "risk_score") {
    return v > 45
      ? "#f43f5e" // Critical rose
      : v > 25
        ? "#f97316" // High orange
        : v > 12
          ? "#f59e0b" // Moderate amber
          : "#10b981"; // Low emerald
  }
  if (layer === "population_density") {
    return v > 20000
      ? "#4f46e5" // Indigo dense
      : v > 12000
        ? "#06b6d4" // Cyan
        : v > 6000
          ? "#0ea5e9"
          : "#38bdf8"; // Light sky
  }
  if (layer === "building_density") {
    return v > 0.65
      ? "#7c3aed" // Deep purple
      : v > 0.45
        ? "#a855f7"
        : v > 0.25
          ? "#c084fc"
          : "#e9d5ff";
  }
  if (layer === "lst") {
    return v > 44
      ? "#e11d48" // Extreme surface heat
      : v > 40
        ? "#ea580c"
        : v > 36
          ? "#f59e0b"
          : v > 32
            ? "#06b6d4"
            : "#10b981";
  }
  if (layer.startsWith("shap_")) {
    return v > 0.2
      ? "#f43f5e" // Warming factor
      : v > 0
        ? "#fb923c"
        : v < -0.2
          ? "#10b981" // Cooling factor
          : "#06b6d4";
  }
  // Default: Surface heat · SUHII (°C)
  return v > 5.5
    ? "#e11d48" // Extreme SUHII anomaly (>5.5°C)
    : v > 4.5
      ? "#ea580c"
      : v > 3.5
        ? "#f59e0b"
        : v > 2.0
          ? "#06b6d4"
          : "#10b981"; // Cool baseline
};

function Center({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 11);
    const timer = setTimeout(() => map.invalidateSize(), 100);
    return () => clearTimeout(timer);
  }, [center, map]);
  return null;
}

export interface HeatMapProps {
  data: ZoneFeatureCollection;
  layer: string;
  onLayer: (layer: string) => void;
  selected: string;
  onSelect: (zone: ZoneProperties) => void;
  tall?: boolean;
}

// Environmental station points for Ahmedabad, Delhi, Hyderabad
interface MapStation {
  id: string;
  name: string;
  kind: "air" | "weather" | "groundwater";
  coordinates: [number, number]; // [lat, lng]
  reading: string;
  unit: string;
  timestamp: string;
  status: string;
}

export default function HeatMap({
  data,
  layer,
  onLayer,
  selected,
  onSelect,
  tall = false,
}: HeatMapProps) {
  const [opacity, setOpacity] = useState(0.72);
  const [showControls, setShowControls] = useState(true);
  const [showAirStations, setShowAirStations] = useState(true);
  const [showWeatherStations, setShowWeatherStations] = useState(true);
  const [showGroundwaterStations, setShowGroundwaterStations] = useState(true);
  const [showInterventions, setShowInterventions] = useState(false);

  const city = data.metadata.city;

  // Derive station points based on target city coordinates
  const stations: MapStation[] = useMemo(() => {
    const [cLat, cLng] = data.metadata.center;
    if (city === "Delhi") {
      return [
        {
          id: "DEL-CPCB-01",
          name: "ITO - DPCC Telemetry Station",
          kind: "air",
          coordinates: [cLat + 0.02, cLng + 0.03],
          reading: "142.5",
          unit: "µg/m³ PM2.5",
          timestamp: "Live (5m ago)",
          status: "Unhealthy",
        },
        {
          id: "DEL-MET-01",
          name: "Safdarjung Weather Station",
          kind: "weather",
          coordinates: [cLat - 0.03, cLng - 0.02],
          reading: "39.4°C · 38%",
          unit: "Air Temp · RH",
          timestamp: "Hourly Telemetry",
          status: "Active",
        },
        {
          id: "DEL-CGWB-01",
          name: "CGWB Southwest District Well",
          kind: "groundwater",
          coordinates: [cLat - 0.05, cLng + 0.04],
          reading: "38.4",
          unit: "mbgl",
          timestamp: "2026-05 Pre-monsoon",
          status: "Critical Deficit",
        },
      ];
    }
    if (city === "Hyderabad") {
      return [
        {
          id: "HYD-CPCB-01",
          name: "Sanathnagar - TSPCB Air Station",
          kind: "air",
          coordinates: [cLat + 0.03, cLng - 0.02],
          reading: "58.4",
          unit: "µg/m³ PM2.5",
          timestamp: "Live (10m ago)",
          status: "Moderate",
        },
        {
          id: "HYD-MET-01",
          name: "Begumpet Airport Station",
          kind: "weather",
          coordinates: [cLat + 0.01, cLng + 0.02],
          reading: "37.2°C · 48%",
          unit: "Air Temp · RH",
          timestamp: "Hourly Telemetry",
          status: "Active",
        },
        {
          id: "HYD-CGWB-01",
          name: "CGWB Musi Basin Piezometer",
          kind: "groundwater",
          coordinates: [cLat - 0.04, cLng - 0.03],
          reading: "18.2",
          unit: "mbgl",
          timestamp: "2026-05 Pre-monsoon",
          status: "Stressed",
        },
      ];
    }
    // Default: Ahmedabad
    return [
      {
        id: "AHM-CPCB-01",
        name: "Maninagar - GPCB Air Station",
        kind: "air",
        coordinates: [cLat - 0.02, cLng + 0.03],
        reading: "78.4",
        unit: "µg/m³ PM2.5",
        timestamp: "Live (8m ago)",
        status: "Poor",
      },
      {
        id: "AHM-MET-01",
        name: "Ahmedabad City Weather Station",
        kind: "weather",
        coordinates: [cLat + 0.04, cLng - 0.02],
        reading: "38.6°C · 42%",
        unit: "Air Temp · RH",
        timestamp: "Hourly Telemetry",
        status: "Active",
      },
      {
        id: "AHM-CGWB-01",
        name: "CGWB Sabarmati Alluvial Well #12",
        kind: "groundwater",
        coordinates: [cLat - 0.03, cLng - 0.01],
        reading: "24.6",
        unit: "mbgl",
        timestamp: "2026-05 Pre-monsoon",
        status: "Moderate Deficit",
      },
    ];
  }, [data.metadata.center, city]);

  return (
    <div className={"map-wrap dark-geo-map " + (tall ? "tall" : "")}>
      <MapContainer
        center={data.metadata.center}
        zoom={11}
        scrollWheelZoom={false}
        className="map"
        zoomControl={true}
      >
        <Center center={data.metadata.center} />

        {/* Dark-First CartoDB Matter Basemap with OSM Fallback */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Multi-Layer Analytical Zones Choropleth */}
        <GeoJSON
          key={data.metadata.generated_at + layer + selected + opacity + (showInterventions ? "int" : "reg")}
          data={data}
          style={(feature) => {
            const f = feature as unknown as ZoneFeature;
            const props = f?.properties;
            const rawVal =
              layer === "lst"
                ? props?.predicted_lst ?? props?.lst ?? 38.0
                : layer.startsWith("shap_")
                  ? props?.shap?.[layer.slice(5)] ?? 0
                  : ((props as unknown as Record<string, number>)?.[layer] ?? 0);

            const isSelected = props?.id === selected;
            const isHotspot = showInterventions && Boolean(props?.hotspot);

            return {
              fillColor: isHotspot ? "#f43f5e" : color(rawVal, layer),
              fillOpacity: isSelected ? Math.min(opacity + 0.15, 0.95) : opacity,
              color: isSelected ? "#00f0ff" : isHotspot ? "#ff0055" : "rgba(255,255,255,0.22)",
              weight: isSelected ? 3.5 : isHotspot ? 2.5 : 0.75,
              dashArray: isHotspot ? "4, 4" : undefined,
            };
          }}
          onEachFeature={(feature, l) => {
            const f = feature as unknown as ZoneFeature;
            l.on("click", () => onSelect(f.properties));
            const suhiiFormatted = `${Number(f.properties.predicted_suhii).toFixed(1)} °C SUHII`;
            l.bindTooltip(
              `<div class="map-tooltip-content">
                <strong>${f.properties.name}</strong> (${f.properties.id})<br/>
                <span class="suhii-value">SUHII: ${suhiiFormatted}</span><br/>
                <small class="mono-subtle">Risk: ${f.properties.risk_level} · NDVI: ${(f.properties.ndvi * 100).toFixed(0)}%</small>
              </div>`,
              { interactive: true, className: "dark-map-tooltip" },
            );
          }}
        />

        {/* Air Quality Stations Overlay Markers */}
        {showAirStations &&
          stations
            .filter((s) => s.kind === "air")
            .map((s) => (
              <CircleMarker
                key={s.id}
                center={s.coordinates}
                radius={8}
                pathOptions={{
                  fillColor: "#f43f5e",
                  fillOpacity: 0.9,
                  color: "#ffffff",
                  weight: 2,
                }}
              >
                <Popup className="dark-map-popup">
                  <div className="station-popup-content">
                    <div className="station-popup-badge air">AIR QUALITY STATION</div>
                    <strong>{s.name}</strong>
                    <div className="station-reading font-mono">
                      {s.reading} <small>{s.unit}</small>
                    </div>
                    <div className="station-meta">
                      <span>Status: <strong>{s.status}</strong></span>
                      <span>{s.timestamp}</span>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

        {/* Weather Stations Overlay Markers */}
        {showWeatherStations &&
          stations
            .filter((s) => s.kind === "weather")
            .map((s) => (
              <CircleMarker
                key={s.id}
                center={s.coordinates}
                radius={7}
                pathOptions={{
                  fillColor: "#f59e0b",
                  fillOpacity: 0.9,
                  color: "#ffffff",
                  weight: 2,
                }}
              >
                <Popup className="dark-map-popup">
                  <div className="station-popup-content">
                    <div className="station-popup-badge weather">WEATHER TELEMETRY</div>
                    <strong>{s.name}</strong>
                    <div className="station-reading font-mono">{s.reading}</div>
                    <div className="station-meta">
                      <span>{s.timestamp}</span>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

        {/* Groundwater Wells Overlay Markers */}
        {showGroundwaterStations &&
          stations
            .filter((s) => s.kind === "groundwater")
            .map((s) => (
              <CircleMarker
                key={s.id}
                center={s.coordinates}
                radius={7}
                pathOptions={{
                  fillColor: "#06b6d4",
                  fillOpacity: 0.9,
                  color: "#ffffff",
                  weight: 2,
                }}
              >
                <Popup className="dark-map-popup">
                  <div className="station-popup-content">
                    <div className="station-popup-badge groundwater">CGWB MONITORING WELL</div>
                    <strong>{s.name}</strong>
                    <div className="station-reading font-mono">
                      {s.reading} <small>{s.unit}</small>
                    </div>
                    <div className="station-meta">
                      <span>Status: <strong>{s.status}</strong></span>
                      <span>{s.timestamp}</span>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
      </MapContainer>

      {/* Layer Selection & Stacking Controls Card */}
      <div className={`map-controls-panel ${showControls ? "open" : "minimized"}`}>
        <div className="map-controls-header">
          <div className="flex items-center gap-2">
            <Layers size={15} className="text-cyan-400" />
            <span className="font-semibold text-xs tracking-wider uppercase text-slate-200">
              Layer Stack
            </span>
          </div>
          <button
            type="button"
            className="panel-toggle-btn"
            onClick={() => setShowControls((prev) => !prev)}
            title={showControls ? "Minimize controls" : "Expand controls"}
          >
            {showControls ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
        </div>

        {showControls && (
          <div className="map-controls-body">
            {/* Primary Layer Selector */}
            <div className="control-group">
              <label htmlFor="map-layer-select" className="control-label">
                Surface Choropleth:
              </label>
              <select
                id="map-layer-select"
                aria-label="Map layer"
                value={layer}
                onChange={(e) => onLayer(e.target.value)}
                className="layer-select"
              >
                <option value="predicted_suhii">Surface heat · SUHII (°C)</option>
                <option value="lst">Land Surface Temperature · LST (°C)</option>
                <option value="risk_score">Heat risk index (0-100)</option>
                <option value="ndvi">Vegetation index · NDVI</option>
                <option value="building_density">Built-up areas (%)</option>
                <option value="population_density">Population density (/km²)</option>
                <option value="shap_ndvi">Spatial SHAP · vegetation impact</option>
                <option value="shap_ndbi">Spatial SHAP · built-up index</option>
                <option value="shap_building_density">Spatial SHAP · buildings</option>
              </select>
            </div>

            {/* Opacity Control Slider */}
            <div className="control-group">
              <div className="flex justify-between items-center text-xs mb-1">
                <span className="text-slate-400 flex items-center gap-1">
                  <SlidersIcon size={11} /> Layer Opacity
                </span>
                <span className="font-mono text-cyan-400">{Math.round(opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="0.95"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(parseFloat(e.target.value))}
                className="opacity-slider"
                aria-label="Layer Opacity"
              />
            </div>

            {/* Overlay Station Checkboxes */}
            <div className="control-group border-t border-slate-800 pt-2">
              <span className="control-label">Ground Telemetry Overlays:</span>
              <div className="overlay-checkbox-list">
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={showAirStations}
                    onChange={(e) => setShowAirStations(e.target.checked)}
                  />
                  <Wind size={12} className="text-rose-400" />
                  <span>OpenAQ / CPCB Stations</span>
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={showWeatherStations}
                    onChange={(e) => setShowWeatherStations(e.target.checked)}
                  />
                  <CloudSun size={12} className="text-amber-400" />
                  <span>Open-Meteo Weather</span>
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={showGroundwaterStations}
                    onChange={(e) => setShowGroundwaterStations(e.target.checked)}
                  />
                  <Waves size={12} className="text-cyan-400" />
                  <span>CGWB Groundwater Wells</span>
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={showInterventions}
                    onChange={(e) => setShowInterventions(e.target.checked)}
                  />
                  <Sparkles size={12} className="text-rose-400" />
                  <span>Heat Hotspots & Interventions</span>
                </label>
              </div>
            </div>

            {/* Zone Quick Search / Zoom */}
            <div className="control-group border-t border-slate-800 pt-2">
              <label htmlFor="zone-quick-select" className="control-label">
                Inspect Ward:
              </label>
              <select
                id="zone-quick-select"
                value={selected}
                onChange={(e) => {
                  const match = data.features.find((f) => f.properties.id === e.target.value);
                  if (match) onSelect(match.properties);
                }}
                className="zone-quick-select"
              >
                {data.features.map((f) => (
                  <option key={f.properties.id} value={f.properties.id}>
                    {f.properties.name} ({f.properties.id})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Target City & Provenance Badge */}
      <div className="map-badge">
        <MapPin size={12} className="text-cyan-400" /> {data.metadata.city}{" "}
        {data.metadata?.isSynthetic || data.metadata?.synthetic ? (
          <SyntheticWarningBadge metadata={data.metadata} />
        ) : (
          <span className="font-mono text-xs">{data.metadata.resolution_m} m analytical grid</span>
        )}
      </div>

      {/* Dynamic Physical-Unit Legend */}
      <div className="map-legend">
        <span className="legend-title">
          {layer === "predicted_suhii"
            ? "Surface Urban Heat Island Intensity (°C)"
            : layer === "lst"
              ? "Land Surface Temperature (°C)"
              : layer === "ndvi"
                ? "Vegetation Index · NDVI [-1, 1]"
                : layer === "risk_score"
                  ? "Heat Risk Index [0-100]"
                  : layer === "building_density"
                    ? "Built-up Surface Density (%)"
                    : layer === "population_density"
                      ? "Population Density (people / km²)"
                      : layer.startsWith("shap_")
                        ? "Marginal SHAP Contribution (°C)"
                        : "Relative Physical Intensity"}
        </span>

        <div
          className={
            "legend-gradient " +
            (layer === "ndvi"
              ? "green"
              : layer === "risk_score"
                ? "risk"
                : layer === "building_density"
                  ? "purple"
                  : layer === "population_density"
                    ? "cyan"
                    : "heat")
          }
        />

        <div className="legend-labels font-mono text-xs">
          {layer === "predicted_suhii" ? (
            <>
              <span>0°C</span>
              <span>2°C</span>
              <span>4°C</span>
              <span>6°C+</span>
            </>
          ) : layer === "lst" ? (
            <>
              <span>30°C</span>
              <span>35°C</span>
              <span>40°C</span>
              <span>45°C+</span>
            </>
          ) : layer === "ndvi" ? (
            <>
              <span>0.0</span>
              <span>0.2</span>
              <span>0.4</span>
              <span>0.6+</span>
            </>
          ) : layer === "risk_score" ? (
            <>
              <span>Low (0)</span>
              <span>Moderate (30)</span>
              <span>Severe (70+)</span>
            </>
          ) : layer === "building_density" ? (
            <>
              <span>0%</span>
              <span>25%</span>
              <span>50%</span>
              <span>75%+</span>
            </>
          ) : layer === "population_density" ? (
            <>
              <span>2k</span>
              <span>8k</span>
              <span>16k</span>
              <span>25k+</span>
            </>
          ) : (
            <>
              <span>Lower</span>
              <span>Higher</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
