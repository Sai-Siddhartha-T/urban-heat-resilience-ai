import React from "react";
import { MapPin, Shield } from "lucide-react";
import type { City, ZoneProperties } from "../../types";

export interface ContextBarProps {
  city: City | string;
  selectedZone?: ZoneProperties | null;
  layer?: string;
  className?: string;
}

export function ContextBar({
  city,
  selectedZone,
  layer,
  className = "",
}: ContextBarProps) {
  if (!selectedZone) return null;

  return (
    <div className={`context-bar flex items-center justify-between text-xs py-2 px-4 bg-emerald-50/60 border-b border-emerald-100 text-emerald-950 ${className}`.trim()}>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1 font-semibold">
          <MapPin size={13} className="text-emerald-700" />
          {city} · {selectedZone.name} ({selectedZone.id})
        </span>
        <span className="text-emerald-700">|</span>
        <span>
          Predicted SUHII: <strong>{Number(selectedZone.predicted_suhii).toFixed(1)}°C</strong>
        </span>
        <span className="text-emerald-700">|</span>
        <span>
          Risk: <strong>{selectedZone.risk_score}</strong> ({selectedZone.risk_level})
        </span>
      </div>

      <div className="flex items-center gap-2 text-emerald-800">
        {selectedZone.protected && (
          <span className="flex items-center gap-1 text-blue-700 font-medium">
            <Shield size={12} /> Protected zoning
          </span>
        )}
        {layer && (
          <span className="text-gray-500">
            Active layer: {layer.replaceAll("_", " ")}
          </span>
        )}
      </div>
    </div>
  );
}
