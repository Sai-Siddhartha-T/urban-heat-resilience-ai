import React from "react";
import { useQuery } from "@tanstack/react-query";
import type { City, CityOverview, MLFeatureName, TreeSHAPExplanation, ZoneFeatureCollection, ZoneProperties } from "../types";
import { mlService } from "../services/mlService";
import { Card } from "../components/common/Card";
import { Notice } from "../components/common/Notice";
import { Pending } from "../components/common/Pending";
import { ZonePicker } from "../components/zone/ZonePicker";
import { ImportanceBarChart } from "../components/charts/ImportanceBarChart";
import HeatMap from "../components/HeatMap";
import { fmt } from "../lib/utils";

export interface ExplainPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
  overview: CityOverview;
}

export function ExplainPage({
  city,
  data,
  selected,
  onSelect,
  overview,
}: ExplainPageProps) {
  const explanation = useQuery<TreeSHAPExplanation>({
    queryKey: ["explain", city, selected.id],
    queryFn: () => mlService.getExplanation(city as City, selected.id),
  });

  return (
    <>
      <div className="section-toolbar">
        <p className="muted">
          Actual TreeSHAP values from the trained {overview.model.winner} model.
        </p>
        <ZonePicker data={data} selected={selected} onSelect={onSelect} />
      </div>

      <div className="two-columns">
        <Card
          title="Global feature importance"
          subtitle="Mean |SHAP| across the analysis grid · °C"
        >
          <ImportanceBarChart data={overview.importance} />
        </Card>

        <Card
          title="Why this zone?"
          subtitle={selected.name + " · Local contribution to predicted SUHII"}
        >
          {explanation.data ? (
            <>
              <ImportanceBarChart
                local
                data={Object.entries(explanation.data.contributions)
                  .map(([feature, importance]) => ({
                    feature: feature as MLFeatureName,
                    importance: Number(importance),
                  }))
                  .sort((a, b) => Math.abs(b.importance) - Math.abs(a.importance))
                  .slice(0, 7)}
              />
              <div className="equation">
                Base {fmt(explanation.data.base_value, 2)}°C + contributions ={" "}
                <strong>{fmt(explanation.data.prediction, 2)}°C</strong>
              </div>
            </>
          ) : explanation.isError ? (
            <Notice tone="warn">
              {explanation.error instanceof Error ? explanation.error.message : "Error computing SHAP values"}
            </Notice>
          ) : (
            <Pending message="Computing TreeSHAP local values…" />
          )}
        </Card>
      </div>

      <Card
        title="How vegetation's contribution varies"
        subtitle="Spatial SHAP: red increases, blue decreases the model prediction"
      >
        <HeatMap
          data={data}
          selected={selected.id}
          onSelect={onSelect}
          layer="shap_ndvi"
          onLayer={() => {}}
        />
      </Card>

      <Notice>
        SHAP explains associations learned by this model. Its values are never
        used as cooling coefficients in the intervention simulator.
      </Notice>
    </>
  );
}
