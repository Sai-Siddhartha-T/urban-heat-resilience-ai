import React from "react";
import type { EvidenceLayer } from "../../types";

type Position = [number, number];
type Geometry = { type: string; coordinates: unknown };

function isPosition(value: unknown): value is Position {
  return Array.isArray(value) &&
    typeof value[0] === "number" &&
    Number.isFinite(value[0]) &&
    typeof value[1] === "number" &&
    Number.isFinite(value[1]);
}

function collectPositions(value: unknown, positions: Position[] = []): Position[] {
  if (isPosition(value)) {
    positions.push(value);
  } else if (Array.isArray(value)) {
    value.forEach((item) => collectPositions(item, positions));
  }
  return positions;
}

function collectGeometries(value: unknown): Geometry[] {
  if (!value || typeof value !== "object") return [];
  const object = value as Record<string, unknown>;

  if (object.type === "FeatureCollection" && Array.isArray(object.features)) {
    return object.features.flatMap(collectGeometries);
  }
  if (object.type === "Feature") return collectGeometries(object.geometry);
  if (object.type === "GeometryCollection" && Array.isArray(object.geometries)) {
    return object.geometries.flatMap(collectGeometries);
  }
  if (typeof object.type === "string" && "coordinates" in object) {
    return [{ type: object.type, coordinates: object.coordinates }];
  }
  return [];
}

function collectFeatureProperties(value: unknown): Record<string, unknown>[] {
  if (!value || typeof value !== "object") return [];
  const object = value as Record<string, unknown>;
  if (object.type === "FeatureCollection" && Array.isArray(object.features)) {
    return object.features.flatMap(collectFeatureProperties);
  }
  if (object.type === "Feature") {
    const properties = object.properties;
    return properties && typeof properties === "object" && !Array.isArray(properties)
      ? [properties as Record<string, unknown>]
      : [];
  }
  return [];
}

function linePath(value: unknown, project: (position: Position) => string): string {
  const points = collectPositions(value);
  return points.map((point, index) => `${index === 0 ? "M" : "L"}${project(point)}`).join(" ");
}

function polygonPath(value: unknown, project: (position: Position) => string): string {
  if (!Array.isArray(value)) return "";
  return value.map((ring) => {
    const points = collectPositions(ring);
    if (!points.length) return "";
    return `${points.map((point, index) => `${index === 0 ? "M" : "L"}${project(point)}`).join(" ")} Z`;
  }).join(" ");
}

function GeometryPreview({ geojson }: { geojson: Record<string, unknown> }) {
  const geometries = collectGeometries(geojson);
  const featureProperties = collectFeatureProperties(geojson);
  const positions = geometries.flatMap((geometry) => collectPositions(geometry.coordinates));
  if (!positions.length) {
    return <p className="muted">The GeoJSON payload contains no renderable coordinate pairs.</p>;
  }

  const xs = positions.map(([x]) => x);
  const ys = positions.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const project = ([x, y]: Position) =>
    `${20 + ((x - minX) / spanX) * 560},${320 - ((y - minY) / spanY) * 300}`;

  return (
    <div>
      <svg
        aria-label="GeoJSON coordinates displayed without reprojection"
        role="img"
        viewBox="0 0 600 340"
        style={{ background: "#f6f8f5", border: "1px solid #dfe7df", borderRadius: 8, maxHeight: 340, width: "100%" }}
      >
        {geometries.map((geometry, index) => {
          const { type, coordinates } = geometry;
          if (type === "Point" && isPosition(coordinates)) {
            const [cx, cy] = project(coordinates).split(",");
            return <circle key={index} cx={cx} cy={cy} r="5" fill="#28744d" />;
          }
          if (type === "MultiPoint" && Array.isArray(coordinates)) {
            return coordinates.filter(isPosition).map((position, pointIndex) => {
              const [cx, cy] = project(position).split(",");
              return <circle key={`${index}-${pointIndex}`} cx={cx} cy={cy} r="5" fill="#28744d" />;
            });
          }
          if (type === "LineString") {
            return <path key={index} d={linePath(coordinates, project)} fill="none" stroke="#28744d" strokeWidth="2" />;
          }
          if (type === "MultiLineString" && Array.isArray(coordinates)) {
            return coordinates.map((line, lineIndex) => (
              <path key={`${index}-${lineIndex}`} d={linePath(line, project)} fill="none" stroke="#28744d" strokeWidth="2" />
            ));
          }
          if (type === "Polygon") {
            return <path key={index} d={polygonPath(coordinates, project)} fill="#77aa7d" fillOpacity="0.35" stroke="#28744d" strokeWidth="2" />;
          }
          if (type === "MultiPolygon" && Array.isArray(coordinates)) {
            return coordinates.map((polygon, polygonIndex) => (
              <path key={`${index}-${polygonIndex}`} d={polygonPath(polygon, project)} fill="#77aa7d" fillOpacity="0.35" stroke="#28744d" strokeWidth="2" />
            ));
          }
          return null;
        })}
      </svg>
      <p className="muted" style={{ marginTop: 6 }}>
        GeoJSON CRS: {geojson.crs ? JSON.stringify(geojson.crs) : "not supplied"}. Displayed from {positions.length} supplied coordinate pair{positions.length === 1 ? "" : "s"}; geometry is fitted to this preview, so scale is schematic and no CRS transformation is applied.
      </p>
      <p className="muted" style={{ marginTop: 3 }}>
        Coordinate extent: x [{minX}, {maxX}], y [{minY}, {maxY}].
      </p>
      {featureProperties.length > 0 && (
        <div style={{ marginTop: 10, overflowX: "auto" }}>
          <table aria-label="GeoJSON feature properties" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th scope="col" style={{ border: "1px solid #dfe7df", padding: "5px 8px", textAlign: "left" }}>Feature</th>
                <th scope="col" style={{ border: "1px solid #dfe7df", padding: "5px 8px", textAlign: "left" }}>Supplied properties</th>
              </tr>
            </thead>
            <tbody>
              {featureProperties.map((properties, index) => (
                <tr key={index}>
                  <td style={{ border: "1px solid #dfe7df", padding: "5px 8px" }}>{index + 1}</td>
                  <td style={{ border: "1px solid #dfe7df", padding: "5px 8px" }}>
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(properties)}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RasterPreview({ layer }: { layer: EvidenceLayer }) {
  const raster = layer.raster;
  if (!raster) return null;

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table aria-label={`${layer.name} raster values`} style={{ borderCollapse: "collapse", fontVariantNumeric: "tabular-nums" }}>
          <tbody>
            {raster.values.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((value, columnIndex) => (
                  <td
                    key={columnIndex}
                    style={{ border: "1px solid #dfe7df", minWidth: 52, padding: "5px 8px", textAlign: "right" }}
                  >
                    {value === null ? "NoData" : value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl style={{ display: "grid", gap: "4px 12px", gridTemplateColumns: "max-content 1fr", margin: "10px 0 0" }}>
        <dt>CRS</dt><dd style={{ margin: 0 }}>{raster.crs || "Not supplied"}</dd>
        <dt>Shape</dt><dd style={{ margin: 0 }}>{raster.shape.join(" × ")}</dd>
        <dt>Affine transform</dt><dd style={{ margin: 0, overflowWrap: "anywhere" }}>[{raster.transform.join(", ")}]</dd>
        <dt>Bounds</dt><dd style={{ margin: 0 }}>{raster.bounds ? `[${raster.bounds.join(", ")}]` : "Not supplied"}</dd>
      </dl>
      <p className="muted" style={{ marginTop: 6 }}>
        Cells show the supplied raster values, not a resampled map. The six-term affine transform and bounds are source metadata; no reprojection or geospatial alignment is performed here.
      </p>
    </div>
  );
}

export function EvidenceLayerPreview({ layer }: { layer: EvidenceLayer }) {
  if (layer.status !== "available") return null;
  if (layer.raster) return <RasterPreview layer={layer} />;
  if (layer.geojson) return <GeometryPreview geojson={layer.geojson} />;
  return <p className="muted">This layer is marked available, but has no GeoJSON or raster payload to render.</p>;
}
