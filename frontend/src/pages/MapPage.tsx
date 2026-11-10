import React from "react";
import type { City, CityOverview, ZoneFeatureCollection, ZoneProperties } from "../types";
import HeatMap from "../components/HeatMap";
import { ZoneDetails } from "../components/zone/ZoneDetails";
import { SyntheticWarningBadge } from "../components/common/SyntheticWarningBadge";

export interface MapPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  overview?: CityOverview;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
  layer: string;
  onLayer: (layer: string) => void;
  navigate: (page: string) => void;
}

export function MapPage({
  data,
  layer,
  onLayer,
  selected,
  onSelect,
  navigate,
}: MapPageProps) {
  const isSynthetic = Boolean(
    data.metadata?.isSynthetic ??
    data.metadata?.synthetic ??
    (typeof data.metadata?.source === "string" && data.metadata.source.toLowerCase().includes("synthetic"))
  );

  return (
    <div className="map-page">
      {isSynthetic && (
        <div className="synthetic-warning-banner" data-testid="map-synthetic-warning">
          <SyntheticWarningBadge metadata={data.metadata}>
            Warning: Map displaying synthetic fallback dataset. Measured spatial accuracy is unvalidated.
          </SyntheticWarningBadge>
        </div>
      )}
      <HeatMap
        data={data}
        layer={layer}
        onLayer={onLayer}
        selected={selected.id}
        onSelect={onSelect}
        tall
      />
      <ZoneDetails selected={selected} navigate={navigate} layer={layer} />
    </div>
  );
}
