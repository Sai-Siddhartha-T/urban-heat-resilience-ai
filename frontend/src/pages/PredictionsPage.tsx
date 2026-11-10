import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import type { City, CityOverview, ModelEvaluation, ZoneFeature, ZoneFeatureCollection } from "../types";
import { mlService } from "../services/mlService";
import { weatherService } from "../services/weatherService";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";
import { WeatherTimeSeriesChart } from "../components/charts/WeatherTimeSeriesChart";
import { fmt } from "../lib/utils";

export interface PredictionsPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  overview: CityOverview;
  notify: (message: string) => void;
  onOpenDataDialog?: () => void;
}

export function PredictionsPage({
  city,
  data,
  overview,
  notify,
  onOpenDataDialog,
}: PredictionsPageProps) {
  const client = useQueryClient();

  const series = useQuery({
    queryKey: ["series", city],
    queryFn: () => weatherService.getWeatherSeries(city),
  });

  const train = useMutation({
    mutationFn: () => mlService.trainModels(city as City),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["overview", city] });
      client.invalidateQueries({ queryKey: ["map", city] });
      notify("Models retrained and spatial evaluation updated.");
    },
  });

  const m = overview.model;
  const splitRecord = m.split as unknown as Record<string, number>;

  return (
    <>
      <div className="section-toolbar">
        <Notice>
          All metrics below are measured on held-out synthetic labels.
          Real-world validation is unavailable.
        </Notice>
        <Button onClick={() => train.mutate()} disabled={train.isPending}>
          <RefreshCw size={15} className={train.isPending ? "spin" : ""} />
          {train.isPending ? "Training…" : "Retrain models"}
        </Button>
      </div>

      {train.isError && (
        <Notice tone="warn">
          {train.error instanceof Error ? train.error.message : "Retraining failed."}
        </Notice>
      )}

      <div className="model-cards">
        {m.evaluations.map((v: ModelEvaluation) => (
          <Card
            key={v.model}
            title={v.model}
            actions={
              m.winner === v.model ? (
                <Badge tone="green">Selected</Badge>
              ) : (
                <Badge tone="neutral">Compared</Badge>
              )
            }
          >
            <div className="model-score">
              {fmt(v.test.r2, 3)}
              <span>R² on test zones</span>
            </div>
            <div className="model-stats">
              <div>
                <small>RMSE</small>
                <strong>{fmt(v.test.rmse, 3)}°C</strong>
              </div>
              <div>
                <small>MAE</small>
                <strong>{fmt(v.test.mae, 3)}°C</strong>
              </div>
              <div>
                <small>Validation RMSE</small>
                <strong>{fmt(v.validation.rmse, 3)}°C</strong>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="two-columns">
        <Card
          title="Observed label vs. prediction"
          subtitle="Spatial test partition only · synthetic SUHII"
        >
          <ResponsiveContainer width="100%" height={330}>
            <ScatterChart margin={{ top: 25, right: 30, bottom: 20, left: 15 }}>
              <CartesianGrid stroke="#e9eeea" />
              <XAxis
                type="number"
                dataKey="observed_suhii"
                name="Synthetic label"
                unit="°C"
              />
              <YAxis
                type="number"
                dataKey="predicted_suhii"
                name="Prediction"
                unit="°C"
              />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <ReferenceLine
                segment={[
                  { x: 0, y: 0 },
                  { x: 7, y: 7 },
                ]}
                stroke="#aaa"
                strokeDasharray="5 5"
              />
              <Scatter
                isAnimationActive={false}
                data={data.features
                  .filter((f: ZoneFeature) => f.properties.partition === "test")
                  .map((f: ZoneFeature) => f.properties)}
                fill="#377e68"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </Card>

        <Card
          title="A spatially separated evaluation"
          subtitle="Model selection uses validation data, not the test set."
        >
          <div className="split-graphic">
            {["training", "validation", "buffer", "test"].map((s, i) => (
              <div
                key={s}
                className={"split s" + i}
                style={{ flex: splitRecord[s] || 1 }}
              >
                <strong>{splitRecord[s] || 0}</strong>
                <span>{s}</span>
              </div>
            ))}
          </div>
          <div className="prose">
            <p>{m.split.method}</p>
            <p>
              <strong>Uncertainty:</strong> ±{fmt(m.interval, 2)}°C from the
              validation set's 90th-percentile absolute residual. This is an
              empirical band; real-world coverage is unknown.
            </p>
            <p>
              <strong>Surface-heat trend:</strong> unavailable. The sample has
              one observation period, so a SUHII trend is not shown.
            </p>
            <p>
              <strong>Model:</strong> {m.winner} selected by lowest validation
              RMSE. Target: urban surface temperature minus the configured rural
              surface-temperature reference.
            </p>
          </div>
        </Card>
      </div>

      {/* Feature 5: Weather Time-Series Visualization */}
      <div className="mt-6">
        <WeatherTimeSeriesChart
          seriesData={series.data}
          isLoading={series.isLoading}
          onOpenDataDialog={onOpenDataDialog}
        />
      </div>
    </>
  );
}
