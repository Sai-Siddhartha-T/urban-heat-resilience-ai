import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { CloudSun, Thermometer, Droplets, ArrowDownToLine, Info } from "lucide-react";
import type { WeatherDataResponse } from "../../types/weather";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";
import { computeWeatherExtremes } from "../../lib/utils";

export interface WeatherTimeSeriesChartProps {
  seriesData?: WeatherDataResponse;
  isLoading?: boolean;
  onOpenDataDialog?: () => void;
  className?: string;
}

export function WeatherTimeSeriesChart({
  seriesData,
  isLoading,
  onOpenDataDialog,
  className = "",
}: WeatherTimeSeriesChartProps) {
  const allSeries = seriesData?.series || [];
  const [selectedIndex, setSelectedIndex] = useState(0);

  if (isLoading) {
    return (
      <div className={`card p-8 text-center text-gray-500 ${className}`}>
        <div className="animate-spin inline-block w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full mb-2"></div>
        <p className="text-sm">Loading meteorological time series…</p>
      </div>
    );
  }

  if (allSeries.length === 0) {
    return (
      <div className={`card p-8 text-center bg-gray-50 border border-dashed border-gray-300 rounded-xl ${className}`}>
        <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-3">
          <CloudSun size={24} />
        </div>
        <h4 className="text-base font-semibold text-gray-900">No Meteorological Time-Series Data</h4>
        <p className="text-sm text-gray-500 max-w-md mx-auto mt-1 mb-4">
          Live atmospheric temperature and humidity records have not been imported for this session yet.
          Ingest Open-Meteo or NASA POWER evidence to populate time-series trends.
        </p>
        {onOpenDataDialog && (
          <Button onClick={onOpenDataDialog} className="inline-flex items-center gap-1.5">
            <ArrowDownToLine size={15} /> Ingest Meteorological Data
          </Button>
        )}
      </div>
    );
  }

  const activeSeries = allSeries[selectedIndex] || allSeries[0];
  const points = activeSeries.points || [];
  const isOpenMeteo = /open[\s-]?meteo/i.test(activeSeries.source);

  const extremes = computeWeatherExtremes(points);
  const maxTemp = extremes.maxTemp !== null ? extremes.maxTemp.toFixed(1) : "—";
  const minTemp = extremes.minTemp !== null ? extremes.minTemp.toFixed(1) : "—";
  const avgHumidity =
    extremes.meanHumidity !== null ? extremes.meanHumidity.toFixed(1) : "—";

  return (
    <div className={`card weather-series-card bg-white rounded-xl border border-gray-200 overflow-hidden ${className}`}>
      {/* Header with Series Selector */}
      <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
              Meteorological time series
            </span>
            <Badge tone="mint">{activeSeries.source.split(" ")[0]}</Badge>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mt-0.5">{activeSeries.variable}</h3>
          <p className="text-xs text-gray-500">
            Location: {activeSeries.latitude.toFixed(3)}°N, {activeSeries.longitude.toFixed(3)}°E · UTC Standard
          </p>
        </div>

        {allSeries.length > 1 && (
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
            {allSeries.map((s, idx) => (
              <button
                key={s.id || idx}
                type="button"
                onClick={() => setSelectedIndex(idx)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                  selectedIndex === idx ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Series {idx + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Summary KPI Chips */}
      <div className="grid grid-cols-3 divide-x divide-gray-200 border-b border-gray-200 bg-gray-50/50">
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Thermometer size={13} className="text-amber-500" /> Peak Air Temp
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{maxTemp} °C</div>
        </div>
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Thermometer size={13} className="text-blue-500" /> Min Air Temp
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{minTemp} °C</div>
        </div>
        <div className="p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-xs text-gray-500">
            <Droplets size={13} className="text-teal-500" /> Mean Humidity
          </div>
          <div className="text-lg font-bold text-gray-900 mt-0.5">{avgHumidity} %</div>
        </div>
      </div>

      {/* Recharts Chart */}
      <div className="p-5" style={{ width: "100%", height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e6edda" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6b7280" }} />
            <YAxis
              yAxisId="temp"
              orientation="left"
              stroke="#d48244"
              unit="°C"
              tick={{ fontSize: 11, fill: "#d48244" }}
              domain={["auto", "auto"]}
            />
            <YAxis
              yAxisId="humidity"
              orientation="right"
              stroke="#4f9999"
              unit="%"
              tick={{ fontSize: 11, fill: "#4f9999" }}
              domain={[0, 100]}
            />
            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toFixed(1)} ${String(name).includes("Temperature") ? "°C" : "%"}`,
                name,
              ]}
              labelFormatter={(lbl) => `Date: ${lbl}`}
              contentStyle={{ background: "#ffffff", borderRadius: "8px", border: "1px solid #e5e7eb" }}
            />
            <Legend verticalAlign="top" height={36} />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="air_temperature_c"
              name="Air Temperature (°C)"
              stroke="#d48244"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#d48244" }}
              activeDot={{ r: 6 }}
            />
            <Line
              yAxisId="humidity"
              type="monotone"
              dataKey="relative_humidity_pct"
              name="Relative Humidity (%)"
              stroke="#4f9999"
              strokeWidth={2}
              strokeDasharray="4 2"
              dot={{ r: 2.5, fill: "#4f9999" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Provenance Footer */}
      <div className="p-3 bg-gray-50 border-t border-gray-200 flex items-start gap-2 text-xs text-gray-500">
        <Info size={14} className="mt-0.5 text-gray-400 shrink-0" />
        <span>
          Air temperature at 2 m measures atmospheric heat, which differs from satellite Land Surface Temperature (LST)
          and Surface Urban Heat Island Intensity (SUHII).{" "}
          {isOpenMeteo
            ? "Open-Meteo values are model-based forecast or reanalysis products, not direct physical station measurements."
            : `Measurement or model status depends on the ${activeSeries.source} product.`}
          {activeSeries.synthetic ? " This series is synthetic." : ""}
        </span>
      </div>
    </div>
  );
}
