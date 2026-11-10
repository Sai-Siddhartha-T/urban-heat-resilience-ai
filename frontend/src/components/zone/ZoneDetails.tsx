import React from "react";
import type { ZoneProperties } from "../../types/geojson";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";
import { fmt } from "../../lib/utils";
import { isRasterLayer } from "../../lib/raster";

export interface ZoneDetailsProps {
  selected: ZoneProperties;
  navigate?: (page: string) => void;
  className?: string;
  layer?: string;
}

export function ZoneDetails({
  selected: p,
  navigate,
  className = "",
  layer,
}: ZoneDetailsProps) {
  return (
    <Card
      title={p.name}
      subtitle={`Zone identifier ${p.id} · ${p.city}`}
      className={className}
      actions={
        <div style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
          {layer && isRasterLayer(layer) && (
            <a
              href="sidecar://biomolecular_structure_viewer"
              className="sidecar-pill-link"
              title="Inspect raster layer in sidecar viewer: sidecar://biomolecular_structure_viewer"
              data-testid="zone-sidecar-link"
            >
              Sidecar Viewer
            </a>
          )}
          <Badge tone={p.protected ? "blue" : "neutral"}>
            {p.protected ? "Protected zoning" : "Standard zoning"}
          </Badge>
        </div>
      }
    >
      <div className="zone-kpis">
        <div>
          <span>Predicted SUHII</span>
          <strong>{Number(p.predicted_suhii).toFixed(1)}°C</strong>
          <small>
            Interval [{Number(p.interval_low).toFixed(1)},{" "}
            {Number(p.interval_high).toFixed(1)}]°C
          </small>
        </div>
        <div>
          <span>Estimated LST</span>
          <strong>{Number(p.predicted_lst).toFixed(1)}°C</strong>
          <small>Rural baseline {p.rural_reference}°C</small>
        </div>
        <div>
          <span>Vegetation (NDVI)</span>
          <strong>{(p.ndvi * 100).toFixed(0)}%</strong>
          <small>Unbuilt land {p.available_land_pct}%</small>
        </div>
        <div>
          <span>Building density</span>
          <strong>{(p.building_density * 100).toFixed(0)}%</strong>
          <small>Roofs {p.roof_pct}% · Roads {p.road_pct}%</small>
        </div>
        <div>
          <span>Population</span>
          <strong>{fmt(p.population, 0)}</strong>
          <small>{fmt(p.population_density, 0)} / km²</small>
        </div>
        <div>
          <span>Heat risk index</span>
          <strong>{p.risk_score} / 100</strong>
          <small>{p.risk_level} priority</small>
        </div>
      </div>
      <div className="zone-actions">
        {navigate && (
          <Button
            type="button"
            onClick={() => navigate("Intervention simulator")}
          >
            Test an intervention in this zone
          </Button>
        )}
        <span className="mono-subtle">
          Spatial partition: {p.partition || "holdout test"}
        </span>
      </div>
    </Card>
  );
}
