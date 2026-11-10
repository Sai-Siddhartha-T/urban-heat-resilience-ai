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
import { calcCoolingPotential } from "../../lib/utils";

export interface ZoneComparisonChartProps {
  zones: ZoneProperties[];
  className?: string;
}

const ZONE_COLORS = ["#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"];

export function ZoneComparisonChart({ zones, className = "" }: ZoneComparisonChartProps) {
  if (!zones || zones.length === 0) return null;

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
        zones.map((z) => [z.id, calcCoolingPotential(z)]),
      ),
    },
  ];

  return (
    <div className={`card comparison-chart-card ${className}`}>
      <div className="card-head">
        <div>
          <h3>Multivariate Zone Profiles</h3>
          <p>Direct comparison of heat hazard, surface features, and cooling capacities.</p>
        </div>
      </div>
      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6edda" />
            <XAxis dataKey="metric" tick={{ fontSize: 12, fill: "#4b5563" }} />
            <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
            <Tooltip
              formatter={(value, name) => {
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
