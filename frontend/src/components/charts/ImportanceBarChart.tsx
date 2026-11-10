import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import type { FeatureImportance } from "../../types/ml";
import { label } from "../../lib/utils";

export interface ImportanceChartItem {
  feature?: string;
  name?: string;
  importance?: number;
  value?: number;
}

export interface ImportanceBarChartProps {
  data: (FeatureImportance | ImportanceChartItem)[];
  local?: boolean;
  className?: string;
}

export function ImportanceBarChart({
  data,
  local = false,
  className = "",
}: ImportanceBarChartProps) {
  const chartData = (data || []).map((d) => {
    const featureName = ("feature" in d && d.feature) ? d.feature : ("name" in d && d.name) ? d.name : "";
    const rawVal = ("importance" in d && d.importance !== undefined) ? d.importance : ("value" in d && d.value !== undefined) ? d.value : 0;
    return {
      name: label(featureName),
      value: Number(rawVal.toFixed(2)),
      positive: rawVal >= 0,
    };
  });

  return (
    <div className={`importance-wrap ${className}`.trim()}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 8, right: 24, left: 24, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="2 4" stroke="#e6edda" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#58716b" }}
            unit={local ? "°C" : ""}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fontSize: 11, fill: "#21403a" }}
          />
          <Tooltip
            formatter={(v) => [
              `${v}${local ? "°C contribution" : " mean |SHAP|"}`,
              "Impact",
            ]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={local ? (entry.positive ? "#dc704e" : "#2c7262") : "#2c7262"}
                fillOpacity={0.88}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
