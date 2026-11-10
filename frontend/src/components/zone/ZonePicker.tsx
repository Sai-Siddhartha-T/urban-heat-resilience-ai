import React from "react";
import type { ZoneFeature, ZoneFeatureCollection, ZoneProperties } from "../../types/geojson";

export interface ZonePickerProps {
  data: ZoneFeatureCollection;
  selected?: ZoneProperties | null;
  onSelect: (zone: ZoneProperties) => void;
  id?: string;
  className?: string;
}

export function ZonePicker({
  data,
  selected,
  onSelect,
  id = "zone-select",
  className = "",
}: ZonePickerProps) {
  return (
    <div className={`zone-picker ${className}`.trim()}>
      <label htmlFor={id}>Focus zone</label>
      <select
        id={id}
        value={selected?.id || ""}
        onChange={(e) => {
          const feature = data.features.find(
            (f: ZoneFeature) => f.properties.id === e.target.value,
          );
          if (feature) onSelect(feature.properties);
        }}
      >
        {data.features.map((f: ZoneFeature) => (
          <option key={f.properties.id} value={f.properties.id}>
            {f.properties.name} · {Number(f.properties.predicted_suhii).toFixed(1)}°C SUHII
            {f.properties.hotspot ? " · Hotspot" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
