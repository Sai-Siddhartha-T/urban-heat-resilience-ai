import React, { useState, useEffect } from "react";
import {
  Thermometer,
  ArrowRight,
  Check,
  Sparkles,
  Scale,
} from "lucide-react";
import type { City, ZoneFeature, ZoneFeatureCollection, ZoneProperties } from "../types";
import { ZoneComparisonChart } from "../components/charts/ZoneComparisonChart";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import {
  fmt,
  calcCoolingPotential,
  updateZoneSelection,
  computeSuhiiDisparity,
} from "../lib/utils";

export interface ZoneComparePageProps {
  city: City | string;
  data: ZoneFeatureCollection | undefined;
  selected?: ZoneProperties;
  onSelect?: (zone: ZoneProperties) => void;
  navigate: (page: string, params?: Record<string, string>) => void;
  notify?: (message: string) => void;
}

export function ZoneComparePage({
  city,
  data,
  onSelect,
  navigate,
}: ZoneComparePageProps) {
  const allZones: ZoneProperties[] = data?.features?.map((f: ZoneFeature) => f.properties) || [];

  // Default to the first two zones (or top 2 hotspots)
  const defaultSelected = allZones.slice(0, 2).map((z) => z.id);
  const [selectedIds, setSelectedIds] = useState<string[]>(defaultSelected);

  // Synchronize or reset selectedIds when city changes or data updates
  useEffect(() => {
    if (allZones.length > 0) {
      const validIds = selectedIds.filter((id) => allZones.some((z) => z.id === id));
      if (validIds.length > 0) {
        if (validIds.length !== selectedIds.length) {
          setSelectedIds(validIds);
        }
      } else {
        setSelectedIds(allZones.slice(0, 2).map((z) => z.id));
      }
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
              type="button"
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
            {selectedZones.length > 0 ? Math.max(...selectedZones.map((z) => calcCoolingPotential(z))).toFixed(2) : "0.00"} °C
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
                    {calcCoolingPotential(z).toFixed(2)} °C
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
                      onClick={() => {
                        onSelect?.(z);
                        navigate("Intervention simulator", { zone: z.id });
                      }}
                    >
                      <ArrowRight size={12} className="mr-1" /> Simulate Interventions
                    </Button>
                    <Button
                      variant="outline"
                      className="text-xs w-full justify-start"
                      onClick={() => {
                        onSelect?.(z);
                        navigate("Explainable AI", { zone: z.id });
                      }}
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
