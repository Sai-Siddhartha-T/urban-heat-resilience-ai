import React from "react";
import type { Tone } from "../../types/common";

export interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  detail: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  tone?: Tone;
  className?: string;
}

export function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  detail,
  tone = "neutral",
  className = "",
}: MetricCardProps) {
  return (
    <div className={`metric-card ${tone}${className ? ` ${className}` : ""}`}>
      <div className="metric-head">
        <span>{label}</span>
        <Icon size={16} />
      </div>
      <div className="metric-value">
        {value}
        {unit && <small>{unit}</small>}
      </div>
      <p>{detail}</p>
    </div>
  );
}
