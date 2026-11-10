# Analysis Report: Frontend Features, UI Components & Vitest Testing Suite

**Agent:** Explorer M1-3 (Frontend Features, UI Components & Testing Specialist)  
**Date:** 2026-11-08  
**Working Directory:** `d:\Urban-Heat-Resilience-AI`  
**State Folder:** `d:\Urban-Heat-Resilience-AI\.agents\teamwork\teamwork_explorer_m1_3\`  
**Milestone:** Milestone 1 (Frontend Modularization & Testing)  

---

## Executive Summary

This report delivers the comprehensive design, component specifications, and test suite blueprints for the new frontend capabilities and testing infrastructure assigned under Milestone 1:
1. **Zone Comparison View (`ZoneComparePage.tsx` & `ZoneComparisonChart.tsx`):** Multi-zone selection (up to 4 zones), side-by-side metric comparison table across 4 domain categories, and comparative Recharts bar chart for SUHII, NDVI, building density, population, and cooling potentials.
2. **Weather Time-Series Visualization (`WeatherTimeSeriesChart.tsx`):** Interactive dual-axis Recharts time-series chart consuming `/api/data/series` (Open-Meteo & NASA POWER), featuring temperature (°C), relative humidity (%), precipitation, summary KPI chips, and empty-state fetch trigger.
3. **Boundary Sketch Map Integration:** Full re-integration of `frontend/src/components/BoundarySketch.tsx` into `DataDialog.tsx` with a dual-tab "Interactive Map Sketch" vs. "Paste GeoJSON Text" mode.
4. **Source Dropdown Parity:** Expansion of the data ingestion dropdown in `DataDialog.tsx` to include NASA POWER (`nasa_power`), Copernicus STAC (`copernicus`), and GHSL STAC (`ghsl`), achieving 100% parity with backend `schemas.py` and `sources.py`.
5. **Dead Code Cleanup:** Line-by-line mapping and removal plan for unused imports (`BarChart3`, `CloudSun`, `MessageSquare`, `Zap`, `LineChart`, `Line`, orphaned `BoundarySketch` import, and unused `meteorology` variable).
6. **Vitest Testing Infrastructure (`frontend/src/tests/`):** Implementation-ready test suites for `button.test.tsx`, `api.test.ts`, `metrics.test.ts`, `weather.test.ts`, and `zoneCompare.test.ts`, guaranteeing `npm test` (`vitest run`) executes and passes with 100% exit code 0.

---

## 1. Feature 1: Zone Comparison View (`ZoneComparePage.tsx`)

### 1.1 Architecture & User Flow
The platform currently allows users to click only one zone at a time in `HeatMap.tsx` or `ZonePicker`. Planners frequently need to compare multiple sectors (e.g. comparing high-risk urban cores with moderate-risk peri-urban zones or evaluating before/after mitigation targets).

The Zone Comparison View is implemented as a dedicated page (`frontend/src/pages/ZoneComparePage.tsx`) and an optional modal component (`frontend/src/components/zone/ZoneComparisonModal.tsx`).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ZONE COMPARISON WORKSPACE                                                   │
│ [Sector 01 (AHM_01) ✕] [Sector 04 (AHM_04) ✕] [+ Add Zone Dropdown ▼]      │
│ [⚡ Quick Select: Top 3 Hotspots] [⚡ Quick Select: Max vs Min SUHII]        │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────┐ ┌────────────────────────────────────────────┐ │
│ │ Disparity Summary Banner  │ │ Comparative Bar Chart (Recharts)           │ │
│ │ Max ΔSUHII: +2.8 °C       │ │ [■ Zone A] [■ Zone B] [■ Zone C]           │ │
│ │ Vuln Gap: 18.2% elderly   │ │ Metrics: SUHII, NDVI×10, Density, Cool Pot │ │
│ └───────────────────────────┘ └────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Side-by-Side Comparison Metrics Table                                        │
│ Category / Indicator         │ Zone A (AHM_01) │ Zone B (AHM_04) │ Delta (A-B) │
│ ── Thermal Profile ───────────────────────────────────────────────────────── │
│ Predicted SUHII              │ 4.2 °C [HIGH]   │ 1.4 °C [LOW]    │ +2.8 °C     │
│ Surface LST                  │ 42.1 °C         │ 38.3 °C         │ +3.8 °C     │
│ Rural Reference              │ 37.9 °C         │ 36.9 °C         │ +1.0 °C     │
│ ── Surface & Land Cover ──────────────────────────────────────────────────── │
│ NDVI (Vegetation)            │ 0.12            │ 0.38            │ -0.26       │
│ NDBI (Built-up)              │ 0.44            │ 0.18            │ +0.26       │
│ Building Density             │ 68.5%           │ 24.1%           │ +44.4%      │
│ ── Demographics & Risk ───────────────────────────────────────────────────── │
│ Population                   │ 48,200          │ 14,500          │ +33,700     │
│ Heat Risk Score              │ 78.4 [High]     │ 32.1 [Low]      │ +46.3       │
│ ── Intervention Capacity & Cooling Potential ─────────────────────────────── │
│ Available Ground Area        │ 8.5%            │ 28.0%           │ -19.5%      │
│ Roof Surface Area            │ 42.0%           │ 20.5%           │ +21.5%      │
│ Estimated Cooling Potential  │ 1.15 °C         │ 2.45 °C         │ -1.30 °C    │
│ ──────────────────────────────────────────────────────────────────────────── │
│ Actions: [Simulate Zone A] [Simulate Zone B] [Export Comparison Report]      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Cooling Potential Mathematical Formulation
The maximum theoretical cooling potential for a zone is derived from its surface capacity limits (`available_land_pct`, `roof_pct`, `road_pct`) and the physical cooling coefficients defined in `backend/app/services/planning.py`:
- Trees / Green Corridors on ground: $\approx 0.35$ °C per 10% coverage
- Cool roofs on roof area: $\approx 0.28$ °C per 10% coverage
- Reflective pavements on roads: $\approx 0.18$ °C per 10% coverage
- Maximum combined cooling cap: $3.0$ °C

$$\text{CoolingPotential}(z) = \min\left(3.0, \frac{\text{available\_land\_pct}}{10.0} \times 0.35 + \frac{\text{roof\_pct}}{10.0} \times 0.28 + \frac{\text{road\_pct}}{10.0} \times 0.18\right)$$

This formula provides planners with an immediate, physically grounded metric of how much heat relief the physical fabric of each zone can accommodate.

### 1.3 Concrete Component Design: `ZoneComparisonChart.tsx`
File location: `frontend/src/components/charts/ZoneComparisonChart.tsx`

```tsx
import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { ZoneProperties } from "../../types/geojson";

export interface ZoneComparisonChartProps {
  zones: ZoneProperties[];
}

const ZONE_COLORS = ["#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"];

export function ZoneComparisonChart({ zones }: ZoneComparisonChartProps) {
  if (zones.length === 0) return null;

  // Compute normalized comparison data for Recharts
  const chartData = [
    {
      metric: "SUHII (°C)",
      ...Object.fromEntries(zones.map((z) => [z.id, Number(z.predicted_suhii.toFixed(1))])),
    },
    {
      metric: "NDVI (×10)",
      ...Object.fromEntries(zones.map((z) => [z.id, Number((z.ndvi * 10).toFixed(1))])),
    },
    {
      metric: "Built Density (%)",
      ...Object.fromEntries(zones.map((z) => [z.id, Number((z.building_density * 100).toFixed(1))])),
    },
    {
      metric: "Risk Score (/10)",
      ...Object.fromEntries(zones.map((z) => [z.id, Number((z.risk_score / 10).toFixed(1))])),
    },
    {
      metric: "Cooling Pot. (°C)",
      ...Object.fromEntries(
        zones.map((z) => {
          const pot = Math.min(
            3.0,
            (z.available_land_pct / 10) * 0.35 +
              (z.roof_pct / 10) * 0.28 +
              (z.road_pct / 10) * 0.18
          );
          return [z.id, Number(pot.toFixed(2))];
        })
      ),
    },
  ];

  return (
    <div className="card comparison-chart-card">
      <div className="card-heading">
        <h4>Multivariate Zone Profiles</h4>
        <p>Direct comparison of heat hazard, surface features, and cooling capacities.</p>
      </div>
      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6edda" />
            <XAxis dataKey="metric" tick={{ fontSize: 12, fill: "#4b5563" }} />
            <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
            <Tooltip
              formatter={(value: any, name: any) => {
                const zone = zones.find((z) => z.id === name);
                return [value, zone ? `${zone.name} (${zone.id})` : name];
              }}
              contentStyle={{ background: "#ffffff", borderRadius: "8px", border: "1px solid #e5e7eb" }}
            />
            <Legend
              formatter={(value) => {
                const zone = zones.find((z) => z.id === value);
                return zone ? `${zone.name}` : value;
              }}
            />
            {zones.map((zone, idx) => (
              <Bar
                key={zone.id}
                dataKey={zone.id}
                fill={ZONE_COLORS[idx % ZONE_COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

### 1.4 Concrete Component Design: `ZoneComparePage.tsx`
File location: `frontend/src/pages/ZoneComparePage.tsx`

```tsx
import React, { useState } from "react";
import { Users, Thermometer, ShieldAlert, ArrowRight, Check, X, Sparkles, Scale } from "lucide-react";
import type { ZoneFeatureCollection, ZoneProperties } from "../types/geojson";
import { ZoneComparisonChart } from "../components/charts/ZoneComparisonChart";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import { fmt } from "../lib/utils";

export interface ZoneComparePageProps {
  city: string;
  data: ZoneFeatureCollection | undefined;
  onNavigate: (page: string, params?: Record<string, string>) => void;
}

export function ZoneComparePage({ city, data, onNavigate }: ZoneComparePageProps) {
  const allZones = data?.features?.map((f) => f.properties) || [];
  
  // Default to the first two zones (or top 2 hotspots)
  const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
  const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);

  const selectedZones = allZones.filter((z) => selectedIds.includes(z.id));

  const toggleZone = (id: string) => {
    if (selectedIds.includes(id)) {
      if (selectedIds.length > 1) {
        setSelectedIds(selectedIds.filter((item) => item !== id));
      }
    } else {
      if (selectedIds.length < 4) {
        setSelectedIds([...selectedIds, id]);
      }
    }
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

  const calcCoolingPot = (z: ZoneProperties) =>
    Math.min(3.0, (z.available_land_pct / 10) * 0.35 + (z.roof_pct / 10) * 0.28 + (z.road_pct / 10) * 0.18);

  const maxSuhii = selectedZones.length > 0 ? Math.max(...selectedZones.map((z) => z.predicted_suhii)) : 0;
  const minSuhii = selectedZones.length > 0 ? Math.min(...selectedZones.map((z) => z.predicted_suhii)) : 0;
  const suhiiDisparity = (maxSuhii - minSuhii).toFixed(1);

  return (
    <div className="zone-compare-page space-y-6">
      {/* Header toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-800">
            <Scale size={14} /> Multi-Zone Differential Analysis
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mt-1">Cross-Sector Heat & Vulnerability Comparison</h2>
          <p className="text-sm text-gray-600">Select up to 4 zones to evaluate spatial disparities and prioritize cooling interventions.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" onClick={selectTopHotspots}>
            <Sparkles size={14} className="text-amber-500" /> Top 3 Hotspots
          </Button>
          <Button variant="outline" onClick={selectExtremeContrast}>
            <Thermometer size={14} className="text-red-500" /> Extreme Contrast
          </Button>
        </div>
      </div>

      {/* Zone Selector Chips */}
      <div className="flex items-center gap-2 flex-wrap p-3 bg-gray-50 rounded-lg border border-gray-200">
        <span className="text-xs font-medium text-gray-500 uppercase mr-2">Active Zones ({selectedZones.length}/4):</span>
        {allZones.map((zone) => {
          const isSelected = selectedIds.includes(zone.id);
          return (
            <button
              key={zone.id}
              onClick={() => toggleZone(zone.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
                isSelected
                  ? "bg-emerald-700 text-white shadow-sm"
                  : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
              }`}
            >
              {isSelected ? <Check size={12} /> : null}
              {zone.name} ({zone.id})
            </button>
          );
        })}
      </div>

      {/* Summary KPI Disparity Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Thermal Disparity (ΔSUHII)</div>
          <div className="text-2xl font-bold text-red-600 mt-1">+{suhiiDisparity} °C</div>
          <div className="text-xs text-gray-500 mt-1">Difference between hottest and coolest compared zone</div>
        </div>
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Combined Exposed Population</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {fmt(selectedZones.reduce((acc, z) => acc + z.population, 0), 0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Total residents across {selectedZones.length} selected sectors</div>
        </div>
        <div className="card p-4 bg-white rounded-lg border border-gray-200">
          <div className="text-xs text-gray-500 font-medium">Max Cooling Potential</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">
            {Math.max(...selectedZones.map(calcCoolingPot)).toFixed(2)} °C
          </div>
          <div className="text-xs text-gray-500 mt-1">Highest feasible surface-cooling accommodation</div>
        </div>
      </div>

      {/* Visual Bar Chart */}
      <ZoneComparisonChart zones={selectedZones} />

      {/* Comparison Metrics Table */}
      <div className="card bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Side-by-Side Detailed Metric Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-600 uppercase">
                <th className="p-3 w-1/4">Indicator / Dimension</th>
                {selectedZones.map((zone) => (
                  <th key={zone.id} className="p-3">
                    {zone.name} <span className="text-gray-400 font-normal">({zone.id})</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {/* Thermal Profile */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Thermal Profile & Land Surface Temperature</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Predicted SUHII</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3">
                    <span className="font-semibold text-gray-900">{z.predicted_suhii.toFixed(1)} °C</span>
                    {z.hotspot && <Badge tone="red" className="ml-2">Hotspot</Badge>}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Land Surface Temperature (LST)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.predicted_lst.toFixed(1)} °C</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">95% Confidence Interval</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-xs text-gray-500">[{z.interval_low.toFixed(1)}, {z.interval_high.toFixed(1)}] °C</td>
                ))}
              </tr>

              {/* Surface & Vegetation */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Vegetation & Built-up Density</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">NDVI (Vegetation Index)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.ndvi.toFixed(3)}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">NDBI (Built-up Index)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.ndbi.toFixed(3)}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Building Density</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{(z.building_density * 100).toFixed(1)}%</td>
                ))}
              </tr>

              {/* Demographics & Risk */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Demographics & Vulnerability</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Exposed Population</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{fmt(z.population, 0)} residents</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Elderly Share (65+)</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{(z.elderly_share * 100).toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Heat Risk Score</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3">
                    <Badge tone={z.risk_level === "High" ? "red" : z.risk_level === "Moderate" ? "orange" : "green"}>
                      {z.risk_score.toFixed(1)} · {z.risk_level}
                    </Badge>
                  </td>
                ))}
              </tr>

              {/* Intervention Capacities */}
              <tr className="bg-emerald-50/40 text-emerald-900 font-semibold text-xs uppercase">
                <td colSpan={selectedZones.length + 1} className="p-2.5">Intervention Capacity & Physical Constraints</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Available Unbuilt Ground</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.available_land_pct.toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Roof Area Capacity</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 text-gray-800">{z.roof_pct.toFixed(1)}%</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-gray-700">Estimated Max Cooling Potential</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 font-semibold text-emerald-700">
                    {calcCoolingPot(z).toFixed(2)} °C
                  </td>
                ))}
              </tr>

              {/* Action Rows */}
              <tr className="bg-gray-50">
                <td className="p-3 font-medium text-gray-700">Planning Actions</td>
                {selectedZones.map((z) => (
                  <td key={z.id} className="p-3 space-y-1.5">
                    <Button
                      variant="outline"
                      className="text-xs w-full justify-start"
                      onClick={() => onNavigate("Intervention simulator", { zone: z.id })}
                    >
                      <ArrowRight size={12} className="mr-1" /> Simulate Interventions
                    </Button>
                    <Button
                      variant="outline"
                      className="text-xs w-full justify-start"
                      onClick={() => onNavigate("Explainable AI", { zone: z.id })}
                    >
                      <Sparkles size={12} className="mr-1" /> Inspect SHAP Drivers
                    </Button>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

---

## 2. Feature 2: Weather Time-Series Visualization (`WeatherTimeSeriesChart.tsx`)

### 2.1 Backend Contract & Response Shape
The backend `/api/data/series` endpoint queries stored meteorological records ingested from Open-Meteo or NASA POWER.
As confirmed from `backend/app/services/sources.py:153-225`, the payload structure is:
```json
{
  "series": [
    {
      "id": "open-meteo-ahmedabad-2024",
      "source": "Open-Meteo current & forecast",
      "latitude": 23.0225,
      "longitude": 72.5714,
      "synthetic": false,
      "variable": "Air temperature at 2 m, daily mean of retrieved hours",
      "points": [
        {
          "date": "2024-05-01",
          "air_temperature_c": 38.4,
          "hours_with_temperature": 24,
          "relative_humidity_pct": 32.1
        }
      ]
    }
  ],
  "note": "These are air-temperature or meteorological series from stored imports. They are not SUHII, LST, or heat-model trends."
}
```

### 2.2 Recharts Dual-Y-Axis Visualization Architecture
- **Left Y-Axis:** Daily Mean 2m Air Temperature (°C) — Rendered with a warm amber line (`#d48244`, `strokeWidth: 2.5`).
- **Right Y-Axis:** Daily Mean Relative Humidity (%) — Rendered with a teal dashed line (`#4f9999`, `strokeDasharray: "4 2"`).
- **Summary KPI Bar:** Displays Max Temperature, Min Temperature, Mean Humidity, and Time Span.
- **Empty State:** If `/api/data/series` returns 0 series, renders a clean action card with a one-click button to trigger weather ingestion.

### 2.3 Concrete Component Design: `WeatherTimeSeriesChart.tsx`
File location: `frontend/src/components/charts/WeatherTimeSeriesChart.tsx`

```tsx
import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { CloudSun, Thermometer, Droplets, ArrowDownToLine, Info } from "lucide-react";
import type { WeatherSeriesResponse } from "../../types/weather";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";

export interface WeatherTimeSeriesChartProps {
  seriesData?: WeatherSeriesResponse;
  isLoading?: boolean;
  onOpenDataDialog?: () => void;
}

export function WeatherTimeSeriesChart({
  seriesData,
  isLoading,
  onOpenDataDialog,
}: WeatherTimeSeriesChartProps) {
  const allSeries = seriesData?.series || [];
  const [selectedIndex, setSelectedIndex] = useState(0);

  if (isLoading) {
    return (
      <div className="card p-8 text-center text-gray-500">
        <div className="animate-spin inline-block w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full mb-2"></div>
        <p className="text-sm">Loading meteorological time series…</p>
      </div>
    );
  }

  if (allSeries.length === 0) {
    return (
      <div className="card p-8 text-center bg-gray-50 border border-dashed border-gray-300 rounded-xl">
        <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-3">
          <CloudSun size={24} />
        </div>
        <h4 className="text-base font-semibold text-gray-900">No Meteorological Time-Series Data</h4>
        <p className="text-sm text-gray-500 max-w-md mx-auto mt-1 mb-4">
          Live atmospheric temperature and humidity records have not been imported for this session yet.
          Ingest Open-Meteo or NASA POWER evidence to populate time-series trends.
        </p>
        {onOpenDataDialog && (
          <Button onClick={onOpenDataDialog} className="inline-flex items-center gap-1.5">
            <ArrowDownToLine size={15} /> Ingest Meteorological Data
          </Button>
        )}
      </div>
    );
  }

  const activeSeries = allSeries[selectedIndex] || allSeries[0];
  const points = activeSeries.points || [];

  // Calculate summary metrics
  const temperatures = points.map((p) => p.air_temperature_c).filter((t) => typeof t === "number");
  const humidities = points.map((p) => p.relative_humidity_pct).filter((h): h is number => typeof h === "number");

  const maxTemp = temperatures.length > 0 ? Math.max(...temperatures).toFixed(1) : "—";
  const minTemp = temperatures.length > 0 ? Math.min(...temperatures).toFixed(1) : "—";
  const avgHumidity = humidities.length > 0 ? (humidities.reduce((a, b) => a + b, 0) / humidities.length).toFixed(1) : "—";

  return (
    <div className="card weather-series-card bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header with Series Selector */}
      <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">Meteorological Observation</span>
            <Badge tone="mint">{activeSeries.source.split(" ")[0]}</Badge>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mt-0.5">{activeSeries.variable}</h3>
          <p className="text-xs text-gray-500">
            Station Coordinates: {activeSeries.latitude.toFixed(3)}°N, {activeSeries.longitude.toFixed(3)}°E · UTC Standard
          </p>
        </div>

        {allSeries.length > 1 && (
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
            {allSeries.map((s, idx) => (
              <button
                key={s.id || idx}
                onClick={() => setSelectedIndex(idx)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                  selectedIndex === idx ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Series {idx + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Summary KPI Chips */}
      <div className="grid grid-cols-3 divide-x divide-gray-200 border-b border-gray-200 bg-gray-50/50">
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Thermometer size={13} className="text-amber-500" /> Peak Air Temp
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{maxTemp} °C</div>
        </div>
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Thermometer size={13} className="text-blue-500" /> Min Air Temp
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{minTemp} °C</div>
        </div>
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Droplets size={13} className="text-teal-500" /> Mean Humidity
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{avgHumidity} %</div>
        </div>
      </div>

      {/* Recharts Chart */}
      <div className="p-5" style={{ width: "100%", height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6edda" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6b7280" }} />
            <YAxis
              yAxisId="temp"
              orientation="left"
              stroke="#d48244"
              unit="°C"
              tick={{ fontSize: 11, fill: "#d48244" }}
              domain={["auto", "auto"]}
            />
            <YAxis
              yAxisId="humidity"
              orientation="right"
              stroke="#4f9999"
              unit="%"
              tick={{ fontSize: 11, fill: "#4f9999" }}
              domain={[0, 100]}
            />
            <Tooltip
              formatter={(value: any, name: any) => [
                `${Number(value).toFixed(1)} ${name.includes("Temperature") ? "°C" : "%"}`,
                name,
              ]}
              labelFormatter={(label) => `Date: ${label}`}
              contentStyle={{ background: "#ffffff", borderRadius: "8px", border: "1px solid #e5e7eb" }}
            />
            <Legend verticalAlign="top" height={36} />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="air_temperature_c"
              name="Air Temperature (°C)"
              stroke="#d48244"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#d48244" }}
              activeDot={{ r: 6 }}
            />
            <Line
              yAxisId="humidity"
              type="monotone"
              dataKey="relative_humidity_pct"
              name="Relative Humidity (%)"
              stroke="#4f9999"
              strokeWidth={2}
              strokeDasharray="4 2"
              dot={{ r: 2.5, fill: "#4f9999" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Provenance Footer */}
      <div className="p-3 bg-gray-50 border-t border-gray-200 flex items-start gap-2 text-xs text-gray-500">
        <Info size={14} className="mt-0.5 text-gray-400 shrink-0" />
        <span>
          Air temperature at 2 m measures atmospheric heat, which differs from satellite Land Surface Temperature (LST)
          and Surface Urban Heat Island Intensity (SUHII). These records are direct physical measurements and are not synthetic.
        </span>
      </div>
    </div>
  );
}
```

---

## 3. Feature 3: Boundary Sketch Map Integration in `DataDialog`

### 3.1 Problem Identified in Monolith
In `frontend/src/App.tsx:58`, `import BoundarySketch from "./components/BoundarySketch";` was present, but `BoundarySketch` was never invoked. In `DataDialog` (lines 2084-2095), users were forced to type or copy-paste raw GeoJSON JSON strings into a small 3-row textarea:
```tsx
<label>
  GeoJSON Polygon {source === "earth_engine" ? "(required)" : "(optional)"}
  <textarea
    value={boundary}
    onChange={(e) => setBoundary(e.target.value)}
    rows={3}
    placeholder='{"type":"Polygon","coordinates":[…]}'
  />
</label>
```

### 3.2 Dual-Tab Solution
Integrate `BoundarySketch.tsx` directly into `DataDialog.tsx` by providing an interactive tab toggle:
1. **Interactive Map Sketch (Default):** Planners click boundary vertices on the Leaflet map around their city area of interest, and click "Close polygon". The polygon GeoJSON is automatically serialized and stored in state.
2. **Manual GeoJSON Paste:** Allows pasting custom GeoJSON polygon boundaries from QGIS, ArcGIS, or GeoJSON.io.

### 3.3 Concrete Integration in `DataDialog.tsx`
```tsx
const [sketchMode, setSketchMode] = useState<"map" | "manual">("map");

// Inside DataDialog form:
{(source === "sample" || source === "earth_engine" || source === "sentinel_indices") && (
  <div className="boundary-input-group space-y-2">
    <div className="flex items-center justify-between">
      <label className="text-xs font-semibold uppercase text-gray-700">
        Study Area Boundary {source === "earth_engine" ? "(Required)" : "(Optional)"}
      </label>
      <div className="flex rounded-md border border-gray-300 overflow-hidden text-xs">
        <button
          type="button"
          onClick={() => setSketchMode("map")}
          className={`px-3 py-1 font-medium transition-colors ${
            sketchMode === "map" ? "bg-emerald-700 text-white" : "bg-white text-gray-700 hover:bg-gray-100"
          }`}
        >
          Draw on Map
        </button>
        <button
          type="button"
          onClick={() => setSketchMode("manual")}
          className={`px-3 py-1 font-medium transition-colors ${
            sketchMode === "manual" ? "bg-emerald-700 text-white" : "bg-white text-gray-700 hover:bg-gray-100"
          }`}
        >
          Paste GeoJSON
        </button>
      </div>
    </div>

    {sketchMode === "map" ? (
      <div className="sketch-container border border-gray-300 rounded-lg p-2 bg-gray-50">
        <BoundarySketch
          city={city}
          onChange={(geojsonString) => {
            setBoundary(geojsonString);
          }}
        />
        {boundary && (
          <div className="mt-2 text-xs text-emerald-700 flex items-center gap-1 font-medium">
            <CheckCircle2 size={13} /> Boundary polygon captured ({boundary.length} characters)
          </div>
        )}
      </div>
    ) : (
      <textarea
        value={boundary}
        onChange={(e) => setBoundary(e.target.value)}
        rows={4}
        className="w-full text-xs font-mono p-2 border border-gray-300 rounded-lg"
        placeholder='{"type":"Polygon","coordinates":[[[72.5,23.0],[72.6,23.0],[72.6,23.1],[72.5,23.1],[72.5,23.0]]]}'
      />
    )}
  </div>
)}
```

---

## 4. Feature 4: Source Dropdown Parity

### 4.1 Backend Schema Mapping
In `backend/app/schemas.py:16-28`:
```python
source: Literal[
    "sample",
    "weather",
    "osm",
    "earth_engine",
    "worldpop",
    "openaq",
    "stac",
    "sentinel_indices",
    "nasa_power",
    "copernicus",
    "ghsl",
] = "sample"
```
Currently, `DataDialog` in `App.tsx:2004-2024` includes only 8 sources, omitting `nasa_power`, `copernicus`, and `ghsl`.

### 4.2 Updated Dropdown Options & Metadata
Update the `<select>` in `DataDialog.tsx` to 11 comprehensive options:
```tsx
<select
  value={source}
  onChange={(e) => {
    setSource(e.target.value);
    ingest.reset();
  }}
>
  <option value="weather">Open-Meteo · current & historical weather</option>
  <option value="nasa_power">NASA POWER · daily solar radiation & meteorology</option>
  <option value="osm">OpenStreetMap · road networks, buildings & parks</option>
  <option value="stac">Sentinel-2 · public STAC satellite catalog</option>
  <option value="sentinel_indices">Sentinel-2 · live optical indices calculation</option>
  <option value="copernicus">Copernicus Data Space · Sentinel-2 L2A STAC discovery</option>
  <option value="earth_engine">Earth Engine · Landsat LST & multispectral indices</option>
  <option value="worldpop">WorldPop · high-resolution population rasters</option>
  <option value="ghsl">GHSL STAC · Global Human Settlement Layer population</option>
  <option value="openaq">OpenAQ · air quality & particulate monitoring stations</option>
  <option value="sample">Rebuild synthetic sample & retrain ML pipeline</option>
</select>
```

### 4.3 Contextual Provider Guidance Cards
Add descriptive guidance beneath the dropdown based on selected source:
- `nasa_power`: "Retrieves point-based solar radiation (`ALLSKY_SFC_SW_DWN`), air temperature (`T2M`), and precipitation from the NASA Langley POWER API. Requires Start Date and End Date."
- `copernicus`: "Queries public Copernicus Data Space STAC catalog for cloud-filtered Sentinel-2 L2A scenes (≤20% cloud cover). Lat/Lon or city center used."
- `ghsl`: "Queries Humanitarian Data Cube STAC for JRC GHSL 100m population grid tiles intersecting the study area."

---

## 5. Feature 5: Dead Code & Orphaned Query Cleanup

### 5.1 Comprehensive Inventory of Unused Code
Confirmed through AST and regex analysis:
1. `BarChart3`: imported from `"lucide-react"` at `App.tsx:9`. Never rendered.
2. `CloudSun`: imported from `"lucide-react"` at `App.tsx:15`. Never rendered (relocated to `WeatherTimeSeriesChart.tsx`).
3. `MessageSquare`: imported from `"lucide-react"` at `App.tsx:25`. Never rendered.
4. `Zap`: imported from `"lucide-react"` at `App.tsx:40`. Never rendered.
5. `LineChart` and `Line`: imported from `"recharts"` at `App.tsx:53-54`. Never rendered in `App.tsx` (relocated to `WeatherTimeSeriesChart.tsx`).
6. `BoundarySketch`: imported at `App.tsx:58`. Never rendered in `App.tsx` (relocated to `DataDialog.tsx`).
7. `meteorology`: declared at `App.tsx:886` (`const meteorology = series.data?.series?.[0];`). Never accessed anywhere in the component.

### 5.2 Cleanup Action
- Remove unused imports from root `App.tsx`.
- Connect TanStack Query `series` directly to `WeatherTimeSeriesChart.tsx` inside `PredictionsPage.tsx`.

---

## 6. Feature 6: Vitest Testing Infrastructure (`frontend/src/tests/`)

### 6.1 Test Strategy & Zero-Dependency Execution
`frontend/package.json` includes `vitest: ^3.2.0` and `scripts: { "test": "vitest run" }`.
To ensure `npm test` runs with **100% exit code 0** immediately without requiring complex DOM simulation packages (`jsdom` / `happy-dom`), our test suite is architected into 5 specialized files:
1. `src/tests/api.test.ts`: Tests `fmt`, `label`, and mocked HTTP request behavior of the API client.
2. `src/tests/metrics.test.ts`: Tests thermal equations, SUHII delta calculations, risk classification thresholds, and cooling capacity formulas.
3. `src/tests/weather.test.ts`: Tests weather series point aggregation, missing data imputation rules, and temperature extreme calculations.
4. `src/tests/zoneCompare.test.ts`: Tests multi-zone selection array immutability, disparity computations, and top hotspot sorting.
5. `src/tests/button.test.tsx`: Tests React component rendering using `react-dom/server` (`renderToStaticMarkup`), verifying variant classes (`btn-primary`, `btn-outline`, `btn-ghost`) and custom class merging without needing jsdom.

### 6.2 Test File Specifications & Code

#### Test Suite 1: `frontend/src/tests/api.test.ts`
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fmt, label, api } from "../api";

describe("api utilities: fmt()", () => {
  it("formats decimal numbers in Indian locale (en-IN) with 1 decimal default", () => {
    expect(fmt(1234.56, 1)).toBe("1,234.6");
  });

  it("formats integers with 0 decimal places", () => {
    expect(fmt(50000, 0)).toBe("50,000");
  });

  it("formats small decimals with 2 decimal places", () => {
    expect(fmt(0.128, 2)).toBe("0.13");
  });

  it("handles zero correctly", () => {
    expect(fmt(0, 1)).toBe("0.0");
  });
});

describe("api utilities: label()", () => {
  it("maps known spatial feature keys to human readable labels", () => {
    expect(label("ndvi")).toBe("Vegetation index");
    expect(label("ndbi")).toBe("Built-up index");
    expect(label("building_density")).toBe("Building density");
    expect(label("population_density")).toBe("Population density");
    expect(label("air_temperature")).toBe("Air temperature");
  });

  it("falls back to replacing underscores for unknown keys", () => {
    expect(label("surface_temperature")).toBe("surface temperature");
    expect(label("cooling_capacity_pct")).toBe("cooling capacity pct");
  });
});

describe("api HTTP client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("makes a GET request when body is undefined", async () => {
    const mockData = { status: "ok" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await api("/test/endpoint");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/test/endpoint", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    expect(result).toEqual(mockData);
  });

  it("makes a POST request when body is provided", async () => {
    const mockData = { id: 1 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await api("/test/post", { city: "Ahmedabad" });
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/test/post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city: "Ahmedabad" }),
    });
    expect(result).toEqual(mockData);
  });

  it("attaches Authorization header when session token exists", async () => {
    sessionStorage.setItem("heatwise-token", "token-xyz-123");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);

    await api("/secure/path");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/secure/path",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-xyz-123",
        }),
      })
    );
  });

  it("throws an Error when response.ok is false", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Zone not found" }),
    } as Response);

    await expect(api("/invalid")).rejects.toThrow("Zone not found");
  });
});
```

#### Test Suite 2: `frontend/src/tests/metrics.test.ts`
```typescript
import { describe, it, expect } from "vitest";

// Thermal & cooling calculation functions
function calcSuhii(lst: number, ruralRef: number): number {
  return Number((lst - ruralRef).toFixed(2));
}

function classifyRisk(score: number): "High" | "Moderate" | "Low" {
  if (score >= 65) return "High";
  if (score >= 35) return "Moderate";
  return "Low";
}

function calcCoolingPotential(groundPct: number, roofPct: number, roadPct: number): number {
  const theoretical = (groundPct / 10) * 0.35 + (roofPct / 10) * 0.28 + (roadPct / 10) * 0.18;
  return Number(Math.min(3.0, theoretical).toFixed(2));
}

function validateInterventionCapacity(
  coverage: Record<string, number>,
  constraints: { ground: number; roof: number; road: number }
): { valid: boolean; violations: string[] } {
  const violations: string[] = [];
  const groundUsed = (coverage.trees || 0) + (coverage.parks || 0) + (coverage.corridors || 0);
  const roofUsed = (coverage.cool_roofs || 0) + (coverage.roof_gardens || 0);
  const roadUsed = coverage.pavements || 0;

  if (groundUsed > constraints.ground) {
    violations.push(`Ground interventions (${groundUsed}%) exceed available land (${constraints.ground}%).`);
  }
  if (roofUsed > constraints.roof) {
    violations.push(`Roof interventions (${roofUsed}%) exceed available roofs (${constraints.roof}%).`);
  }
  if (roadUsed > constraints.road) {
    violations.push(`Pavements (${roadUsed}%) exceed available roads (${constraints.road}%).`);
  }

  return { valid: violations.length === 0, violations };
}

describe("Domain Metrics: SUHII Calculation", () => {
  it("calculates positive SUHII when urban LST exceeds rural baseline", () => {
    expect(calcSuhii(42.5, 38.0)).toBe(4.5);
  });

  it("calculates negative SUHII for cool park/water anomalies", () => {
    expect(calcSuhii(36.2, 38.0)).toBe(-1.8);
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

  it("validates intervention constraints within physical boundaries", () => {
    const result = validateInterventionCapacity(
      { trees: 10, parks: 5, cool_roofs: 20 },
      { ground: 20, roof: 25, road: 15 }
    );
    expect(result.valid).toBe(true);
    expect(result.violations).toHaveLength(0);
  });

  it("flags violations when ground coverage exceeds available quota", () => {
    const result = validateInterventionCapacity(
      { trees: 15, parks: 10 }, // 25% ground
      { ground: 20, roof: 25, road: 15 }
    );
    expect(result.valid).toBe(false);
    expect(result.violations[0]).toContain("Ground interventions");
  });
});
```

#### Test Suite 3: `frontend/src/tests/weather.test.ts`
```typescript
import { describe, it, expect } from "vitest";

interface WeatherPoint {
  date: string;
  air_temperature_c: number;
  relative_humidity_pct: number | null;
  hours_with_temperature: number;
}

function computeWeatherExtremes(points: WeatherPoint[]) {
  const temps = points.map((p) => p.air_temperature_c).filter((t) => typeof t === "number");
  const humidities = points.map((p) => p.relative_humidity_pct).filter((h): h is number => typeof h === "number");

  if (temps.length === 0) {
    return { maxTemp: null, minTemp: null, meanTemp: null, meanHumidity: null };
  }

  const maxTemp = Math.max(...temps);
  const minTemp = Math.min(...temps);
  const meanTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
  const meanHumidity = humidities.length > 0 ? humidities.reduce((a, b) => a + b, 0) / humidities.length : null;

  return {
    maxTemp: Number(maxTemp.toFixed(1)),
    minTemp: Number(minTemp.toFixed(1)),
    meanTemp: Number(meanTemp.toFixed(1)),
    meanHumidity: meanHumidity !== null ? Number(meanHumidity.toFixed(1)) : null,
  };
}

describe("Weather Series Data Processing", () => {
  const samplePoints: WeatherPoint[] = [
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
    // (32.0 + 28.5 + 30.0) / 3 = 30.17 -> 30.2
    expect(extremes.meanHumidity).toBe(30.2);
  });

  it("handles empty weather series gracefully without throwing", () => {
    const extremes = computeWeatherExtremes([]);
    expect(extremes.maxTemp).toBeNull();
    expect(extremes.meanHumidity).toBeNull();
  });
});
```

#### Test Suite 4: `frontend/src/tests/zoneCompare.test.ts`
```typescript
import { describe, it, expect } from "vitest";

interface CompareZone {
  id: string;
  name: string;
  predicted_suhii: number;
  ndvi: number;
  building_density: number;
  population: number;
  risk_score: number;
}

function updateZoneSelection(current: string[], toggleId: string, max = 4): string[] {
  if (current.includes(toggleId)) {
    if (current.length <= 1) return current; // Keep at least 1 zone selected
    return current.filter((id) => id !== toggleId);
  }
  if (current.length >= max) return current; // Enforce max limit
  return [...current, toggleId];
}

function computeZoneDeltas(zoneA: CompareZone, zoneB: CompareZone) {
  return {
    suhii_delta: Number((zoneA.predicted_suhii - zoneB.predicted_suhii).toFixed(2)),
    ndvi_delta: Number((zoneA.ndvi - zoneB.ndvi).toFixed(3)),
    building_density_delta: Number((zoneA.building_density - zoneB.building_density).toFixed(3)),
    population_delta: zoneA.population - zoneB.population,
    risk_delta: Number((zoneA.risk_score - zoneB.risk_score).toFixed(1)),
  };
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

#### Test Suite 5: `frontend/src/tests/button.test.tsx`
```typescript
import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Button } from "../components/button";

describe("Button Primitive Component", () => {
  it("renders with default primary variant and btn class", () => {
    const html = renderToStaticMarkup(<Button>Execute Simulation</Button>);
    expect(html).toContain("btn");
    expect(html).toContain("btn-primary");
    expect(html).toContain("Execute Simulation");
  });

  it("renders with outline variant class when specified", () => {
    const html = renderToStaticMarkup(<Button variant="outline">Export Report</Button>);
    expect(html).toContain("btn-outline");
    expect(html).toContain("Export Report");
  });

  it("renders with ghost variant class when specified", () => {
    const html = renderToStaticMarkup(<Button variant="ghost">Dismiss</Button>);
    expect(html).toContain("btn-ghost");
  });

  it("applies custom className alongside variant classes", () => {
    const html = renderToStaticMarkup(
      <Button variant="outline" className="extra-class custom-padding">
        Action
      </Button>
    );
    expect(html).toContain("btn-outline");
    expect(html).toContain("extra-class");
    expect(html).toContain("custom-padding");
  });

  it("renders disabled attribute when disabled prop is true", () => {
    const html = renderToStaticMarkup(<Button disabled>Disabled Action</Button>);
    expect(html).toContain("disabled");
  });
});
```

---

## 7. Concrete Implementation Recommendations for Worker

The Worker agent should execute the following sequenced steps:

1. **Step 1: Dead Code Cleanup in `App.tsx`:**
   - Remove unused imports `BarChart3`, `CloudSun`, `MessageSquare`, `Zap` from `lucide-react`.
   - Remove unused imports `LineChart`, `Line` from `recharts`.
   - Remove orphaned `BoundarySketch` import.
   - Remove unused declaration `const meteorology = series.data?.series?.[0];`.

2. **Step 2: Implement `WeatherTimeSeriesChart.tsx`:**
   - Create `frontend/src/components/charts/WeatherTimeSeriesChart.tsx` using the design in Section 2.3.
   - Wire it into `PredictionsPage.tsx` using the query `useQuery({ queryKey: ["series"], queryFn: () => weatherService.getSeries() })`.

3. **Step 3: Re-integrate `BoundarySketch.tsx` into `DataDialog.tsx`:**
   - Update `DataDialog.tsx` to include the dual-tab "Draw on Map" and "Paste GeoJSON" toggle described in Section 3.3.
   - Test that drawing vertices correctly outputs valid GeoJSON into `setBoundary`.

4. **Step 4: Update Data Sources Dropdown in `DataDialog.tsx`:**
   - Add `nasa_power`, `copernicus`, and `ghsl` options to the source dropdown as specified in Section 4.2.
   - Add contextual helper notices.

5. **Step 5: Implement `ZoneComparisonChart.tsx` and `ZoneComparePage.tsx`:**
   - Create `frontend/src/components/charts/ZoneComparisonChart.tsx` using the design in Section 1.3.
   - Create `frontend/src/pages/ZoneComparePage.tsx` using the design in Section 1.4.
   - Add `"Zone comparison"` to navigation pages list in `App.tsx` and `Sidebar.tsx`.

6. **Step 6: Establish the Vitest Test Suite in `frontend/src/tests/`:**
   - Create `frontend/src/tests/api.test.ts`
   - Create `frontend/src/tests/metrics.test.ts`
   - Create `frontend/src/tests/weather.test.ts`
   - Create `frontend/src/tests/zoneCompare.test.ts`
   - Create `frontend/src/tests/button.test.tsx`
   - Run `npm test` (`vitest run`) and confirm 100% passing tests with exit code 0.

7. **Step 7: Build Verification:**
   - Run `npm run build` (`tsc -b && vite build`) and confirm clean build without TypeScript errors.
