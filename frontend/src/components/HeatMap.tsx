import { useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import { Layers, MapPin } from "lucide-react";
import "leaflet/dist/leaflet.css";
const color = (v: number, layer: string) => {
  if (layer === "ndvi")
    return v > 0.6
      ? "#297d5a"
      : v > 0.4
        ? "#67a967"
        : v > 0.2
          ? "#b2cb83"
          : "#e1dfab";
  if (layer === "risk_score")
    return v > 20 ? "#a42c47" : v > 8 ? "#ee8556" : "#f2d78b";
  if (layer === "population_density")
    return v > 16000 ? "#225c70" : v > 8000 ? "#66a1a5" : "#c4dfd8";
  if (layer === "building_density")
    return v > 0.7 ? "#5d506e" : v > 0.4 ? "#9d8f9f" : "#d9cbd4";
  if (layer === "shap_ndvi") return v > 0 ? "#dc704e" : "#568bab";
  return v > 5
    ? "#a73342"
    : v > 4
      ? "#dd6549"
      : v > 3
        ? "#efa263"
        : v > 2
          ? "#edca80"
          : "#c5d3a3";
};
function Center({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 11);
    setTimeout(() => map.invalidateSize(), 100);
  }, [center[0], center[1], map]);
  return null;
}
export default function HeatMap({
  data,
  layer,
  onLayer,
  selected,
  onSelect,
  tall = false,
}: {
  data: any;
  layer: string;
  onLayer: (v: string) => void;
  selected: string;
  onSelect: (p: any) => void;
  tall?: boolean;
}) {
  return (
    <div className={"map-wrap " + (tall ? "tall" : "")}>
      <MapContainer
        center={data.metadata.center}
        zoom={11}
        scrollWheelZoom={false}
        className="map"
        zoomControl={true}
      >
        <Center center={data.metadata.center} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="/api/tiles/{z}/{x}/{y}.png"
        />
        <GeoJSON
          key={data.metadata.generated_at + layer + selected}
          data={data}
          style={(f: any) => ({
            fillColor: color(
              layer === "shap_ndvi"
                ? f.properties.shap.ndvi
                : f.properties[layer],
              layer,
            ),
            fillOpacity: 0.69,
            color: f.properties.id === selected ? "#143e38" : "#fff",
            weight: f.properties.id === selected ? 3 : 0.4,
          })}
          onEachFeature={(feature, l) => {
            l.on("click", () => onSelect(feature.properties));
            l.bindTooltip(
              `${feature.properties.name} · ${Number(feature.properties.predicted_suhii).toFixed(1)}°C SUHII`,
            );
          }}
        />
      </MapContainer>
      <div className="map-layer">
        <Layers size={15} />
        <select
          aria-label="Map layer"
          value={layer}
          onChange={(e) => onLayer(e.target.value)}
        >
          <option value="predicted_suhii">Surface heat · SUHII</option>
          <option value="risk_score">Heat risk</option>
          <option value="ndvi">Vegetation · NDVI</option>
          <option value="building_density">Built-up areas</option>
          <option value="population_density">Population density</option>
          <option value="shap_ndvi">Spatial SHAP · NDVI</option>
        </select>
      </div>
      <div className="map-badge">
        <MapPin size={12} /> {data.metadata.city}{" "}
        <span>1 km grid · Synthetic</span>
      </div>
      <div className="map-legend">
        <span>
          {layer === "predicted_suhii"
            ? "Surface temperature difference (°C)"
            : layer === "shap_ndvi"
              ? "NDVI contribution (°C)"
              : "Relative layer intensity"}
        </span>
        <div
          className={"legend-gradient " + (layer === "ndvi" ? "green" : "")}
        />
        <div className="legend-labels">
          {layer === "predicted_suhii" ? (
            <>
              <span>0</span>
              <span>2</span>
              <span>4</span>
              <span>6+</span>
            </>
          ) : (
            <>
              <span>Lower</span>
              <span>Higher</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
