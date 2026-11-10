import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, Database, CheckCircle2, MapPin } from "lucide-react";
import type { City, DataIngestRequest } from "../../types";
import { dataService } from "../../services/dataService";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";
import { Notice } from "../common/Notice";
import BoundarySketch from "../BoundarySketch";

export interface DataDialogProps {
  city: City | string;
  close: () => void;
  notify: (message: string) => void;
  onDemoMode: () => void;
}

export function DataDialog({ city, close, notify, onDemoMode }: DataDialogProps) {
  const client = useQueryClient();
  const [source, setSource] = useState("weather");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [boundary, setBoundary] = useState("");
  const [sketchMode, setSketchMode] = useState<"map" | "manual">("map");
  const [rural, setRural] = useState(33);
  const [satelliteProduct, setSatelliteProduct] = useState("landsat");

  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => dataService.getDataStatus(),
  });

  const ingest = useMutation({
    mutationFn: () => {
      const body: DataIngestRequest = {
        city: city as City,
        source,
        rural_reference: rural,
        satellite_product: satelliteProduct,
      };
      if (lat || lon) {
        body.latitude = Number(lat);
        body.longitude = Number(lon);
      }
      if (start || end) {
        body.start_date = start;
        body.end_date = end;
      }
      if (boundary.trim()) {
        try {
          body.boundary = JSON.parse(boundary);
        } catch {
          body.boundary = boundary;
        }
      }
      return dataService.ingestData(body);
    },
    onSuccess: (result) => {
      if (
        result &&
        typeof result === "object" &&
        "mode" in result &&
        result.mode === "demo"
      ) {
        try {
          if (typeof window !== "undefined") {
            window.sessionStorage.setItem("heatwise-mode", "demo");
          }
        } catch {
          // Session storage may be unavailable in restricted browser contexts.
        }
        onDemoMode();
      }
      client.invalidateQueries();
      notify("Ingestion completed. Source and provenance saved.");
    },
  });

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <button
          type="button"
          className="modal-close"
          aria-label="Close data sources"
          onClick={close}
        >
          <X size={18} />
        </button>
        <div className="eyebrow">DATA WORKSPACE</div>
        <h2>Know where your data comes from.</h2>
        <p>Live evidence stays separate from synthetic predictions.</p>

        <div className="data-form">
          <label>
            Data source
            <select
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                ingest.reset();
              }}
            >
              <option value="weather">
                Open-Meteo · current / historical weather
              </option>
              <option value="nasa_power">
                NASA POWER · daily solar radiation & meteorology
              </option>
              <option value="osm">OpenStreetMap · geographical features</option>
              <option value="stac">
                Sentinel-2 · public satellite catalog
              </option>
              <option value="sentinel_indices">
                Sentinel-2 · process live optical indices
              </option>
              <option value="copernicus">
                Copernicus Data Space · Sentinel-2 L2A STAC discovery
              </option>
              <option value="earth_engine">
                Earth Engine · Landsat LST & indices
              </option>
              <option value="worldpop">
                WorldPop · population dataset catalog
              </option>
              <option value="ghsl">
                GHSL STAC · Global Human Settlement Layer population
              </option>
              <option value="openaq">
                OpenAQ · optional monitoring stations
              </option>
              <option value="demo">Demo Mode · synthetic, labelled data</option>
            </select>
          </label>

          {/* Contextual Provider Guidance */}
          {source === "nasa_power" && (
            <div className="text-xs text-gray-500 bg-amber-50/60 p-2.5 rounded border border-amber-200">
              Retrieves point-based solar radiation (ALLSKY_SFC_SW_DWN), air temperature (T2M), and precipitation from the NASA POWER API.
            </div>
          )}
          {source === "copernicus" && (
            <div className="text-xs text-gray-500 bg-blue-50/60 p-2.5 rounded border border-blue-200">
              Queries public Copernicus Data Space STAC catalog for cloud-filtered Sentinel-2 L2A scenes (≤20% cloud cover).
            </div>
          )}
          {source === "ghsl" && (
            <div className="text-xs text-gray-500 bg-emerald-50/60 p-2.5 rounded border border-emerald-200">
              Queries Humanitarian Data Cube STAC for JRC GHSL 100m population grid tiles intersecting the study area.
            </div>
          )}

          {source === "earth_engine" && (
            <label>
              Satellite product
              <select
                aria-label="Satellite product"
                value={satelliteProduct}
                onChange={(e) => setSatelliteProduct(e.target.value)}
              >
                <option value="landsat">Landsat 8/9 · LST and indices</option>
                <option value="sentinel">Sentinel-2 · optical indices</option>
                <option value="modis">MODIS · eight-day daytime LST</option>
                <option value="worldcover">
                  ESA WorldCover · 2021 land cover
                </option>
                <option value="srtm">NASA SRTM · elevation</option>
              </select>
            </label>
          )}

          <div className="two-columns">
            <label>
              Latitude (optional)
              <input
                type="number"
                step="any"
                value={lat}
                placeholder="City center"
                onChange={(e) => setLat(e.target.value)}
              />
            </label>
            <label>
              Longitude (optional)
              <input
                type="number"
                step="any"
                value={lon}
                placeholder="City center"
                onChange={(e) => setLon(e.target.value)}
              />
            </label>
          </div>

          <div className="two-columns">
            <label>
              Start date (optional)
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label>
              End date (optional)
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>
          </div>

          {(source === "demo" || source === "earth_engine" || source === "sentinel_indices") && (
            <div className="boundary-group space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase text-gray-700">
                  Study Area Boundary {source === "earth_engine" ? "(Required)" : "(Optional)"}
                </label>
                <div className="flex rounded border border-gray-300 overflow-hidden text-xs">
                  <button
                    type="button"
                    onClick={() => setSketchMode("map")}
                    className={`px-3 py-1 font-medium transition-colors ${
                      sketchMode === "map"
                        ? "bg-emerald-700 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    Draw on map
                  </button>
                  <button
                    type="button"
                    onClick={() => setSketchMode("manual")}
                    className={`px-3 py-1 font-medium transition-colors ${
                      sketchMode === "manual"
                        ? "bg-emerald-700 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    Paste GeoJSON
                  </button>
                </div>
              </div>

              {sketchMode === "map" ? (
                <div className="sketch-container border border-gray-300 rounded-lg p-2 bg-gray-50">
                  <BoundarySketch
                    city={city}
                    onChange={(geojsonString) => {
                      setBoundary(geojsonString);
                    }}
                  />
                  {boundary && (
                    <div className="mt-2 text-xs text-emerald-700 flex items-center gap-1 font-medium">
                      <CheckCircle2 size={13} /> Boundary polygon captured ({boundary.length} chars)
                    </div>
                  )}
                </div>
              ) : (
                <textarea
                  value={boundary}
                  onChange={(e) => setBoundary(e.target.value)}
                  rows={3}
                  className="w-full text-xs font-mono p-2 border border-gray-300 rounded"
                  placeholder='{"type":"Polygon","coordinates":[[[72.5,23.0],[72.6,23.0],[72.6,23.1],[72.5,23.1],[72.5,23.0]]]}'
                />
              )}

              {source === "demo" && (
                <label className="mt-2 block">
                  Demo-only rural reference LST (°C)
                  <input
                    type="number"
                    value={rural}
                    onChange={(e) => setRural(+e.target.value)}
                  />
                </label>
              )}
            </div>
          )}

          <Button
            onClick={() => ingest.mutate()}
            disabled={ingest.isPending || Boolean(lat) !== Boolean(lon)}
          >
            <Database size={16} />
            {ingest.isPending
              ? "Retrieving and validating…"
              : "Ingest selected source"}
          </Button>

          {ingest.isError && (
            <Notice tone="warn">
              {ingest.error instanceof Error ? ingest.error.message : "Ingestion failed"}
            </Notice>
          )}

          {ingest.data && (
            <div className="ingestion-result">
              <Badge tone="green">
                <CheckCircle2 size={13} className="mr-1 inline" />
                {("mode" in ingest.data && ingest.data.mode === "demo") ? "Demo Mode activated" : "Evidence retrieved"}
              </Badge>
              <p>
                {("source" in ingest.data && typeof ingest.data.source === "string" ? ingest.data.source : "Source recorded")} ·{" "}
                {("mode" in ingest.data && ingest.data.mode === "demo")
                  ? "Synthetic demonstration data"
                  : "Live evidence stored separately; it is not promoted to analysis."}
              </p>
              <details>
                <summary>Inspect retrieved evidence</summary>
                <pre>
                  {JSON.stringify(ingest.data, null, 2).slice(0, 18000)}
                </pre>
              </details>
            </div>
          )}
        </div>

        <h3 className="catalog-title">Satellite & environmental coverage</h3>
        {status.data?.catalog?.map((d: any, idx: number) => (
          <div className="source-row" key={d.id || d.name || idx}>
            <div>
              {d.name || d.id}
              <small className="block muted">{d.description || d.resolution || d.type}</small>
            </div>
            <span className="muted">
              {d.live_configured ? "Live configured" : (d.status || "Synthetic mode")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
