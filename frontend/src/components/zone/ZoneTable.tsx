import React from "react";
import type { ZoneProperties } from "../../types/geojson";
import { Badge } from "../common/Badge";
import { fmt } from "../../lib/utils";

export interface ZoneTableProps {
  zones: ZoneProperties[];
  onSelect: (zone: ZoneProperties) => void;
  selectedId?: string;
  className?: string;
}

export function ZoneTable({
  zones,
  onSelect,
  selectedId,
  className = "",
}: ZoneTableProps) {
  return (
    <div className={`zone-table-wrap ${className}`.trim()}>
      <table className="zone-table">
        <thead>
          <tr>
            <th>Zone</th>
            <th>SUHII</th>
            <th>Risk</th>
            <th>Vegetation</th>
            <th>Buildings</th>
            <th>Population</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {zones.map((p: ZoneProperties) => (
            <tr key={p.id} className={p.id === selectedId ? "selected-row" : ""}>
              <td>
                <strong>{p.name}</strong>
                <small>{p.id}</small>
              </td>
              <td>
                <span className="mono">
                  {Number(p.predicted_suhii).toFixed(1)}°C
                </span>
                {p.hotspot && (
                  <Badge tone="red" className="ml">
                    Hotspot
                  </Badge>
                )}
              </td>
              <td>
                <Badge
                  tone={
                    p.risk_level === "High"
                      ? "red"
                      : p.risk_level === "Moderate"
                        ? "orange"
                        : "green"
                  }
                >
                  {p.risk_score} · {p.risk_level}
                </Badge>
              </td>
              <td>{(p.ndvi * 100).toFixed(0)}%</td>
              <td>{(p.building_density * 100).toFixed(0)}%</td>
              <td>{fmt(p.population, 0)}</td>
              <td>
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => onSelect(p)}
                >
                  Inspect
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
