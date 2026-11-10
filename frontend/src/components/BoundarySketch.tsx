import { useEffect, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const centers: Record<string, [number, number]> = {
  Ahmedabad: [23.0225, 72.5714],
  Delhi: [28.6139, 77.209],
  Hyderabad: [17.385, 78.4867],
};

function Clicks({
  disabled,
  onClick,
}: {
  disabled: boolean;
  onClick: (lon: number, lat: number) => void;
}) {
  useMapEvents({
    click(event) {
      if (!disabled) onClick(event.latlng.lng, event.latlng.lat);
    },
  });
  return null;
}

function Focus({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 12);
    setTimeout(() => map.invalidateSize(), 80);
  }, [center, map]);
  return null;
}

export default function BoundarySketch({
  city,
  onChange,
}: {
  city: string;
  onChange: (geojson: string) => void;
}) {
  const [ring, setRing] = useState<number[][]>([]);
  const [closed, setClosed] = useState(false);
  const center = centers[city] || centers.Ahmedabad;
  const geometry = closed
    ? { type: "Polygon" as const, coordinates: [ring] }
    : { type: "LineString" as const, coordinates: ring };
  const collection =
    ring.length > 0
      ? {
          type: "FeatureCollection" as const,
          features: [
            { type: "Feature" as const, properties: {}, geometry },
          ],
        }
      : null;

  return (
    <div className="sketch">
      <p>
        Click corners on the map, then close the polygon. The result is sent as
        GeoJSON and is not stored until you ingest it.
      </p>
      <div className="sketch-map">
        <MapContainer
          center={center}
          zoom={12}
          className="map"
          scrollWheelZoom={false}
        >
          <Focus center={center} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="/api/tiles/{z}/{x}/{y}.png"
          />
          <Clicks
            disabled={closed}
            onClick={(lon, lat) => setRing((current) => [...current, [lon, lat]])}
          />
          {collection && (
            <GeoJSON key={JSON.stringify(ring) + String(closed)} data={collection} />
          )}
        </MapContainer>
      </div>
      <div className="sketch-actions">
        <button
          type="button"
          onClick={() => {
            if (ring.length < 3) return;
            const polygon = [...ring, ring[0]];
            setRing(polygon);
            setClosed(true);
            onChange(
              JSON.stringify({ type: "Polygon", coordinates: [polygon] }),
            );
          }}
        >
          Close polygon
        </button>
        <button
          type="button"
          onClick={() => {
            setRing([]);
            setClosed(false);
            onChange("");
          }}
        >
          Clear sketch
        </button>
        <span>
          {ring.length} vertices
          {closed ? " · polygon ready" : " · click the map to add corners"}
        </span>
      </div>
    </div>
  );
}
