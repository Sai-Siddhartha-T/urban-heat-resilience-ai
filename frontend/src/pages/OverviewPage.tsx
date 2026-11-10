import React from "react";
import {
  Map as MapIcon,
  Thermometer,
  Sun,
  Users,
  ArrowUpRight,
  Sparkles,
  TreePine,
  Target,
  ArrowRight,
  FlaskConical,
  Network,
} from "lucide-react";
import type { City, CityOverview, ZoneFeatureCollection, ZoneProperties } from "../types";
import { MetricCard } from "../components/common/MetricCard";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Notice } from "../components/common/Notice";
import HeatMap from "../components/HeatMap";
import { ZoneTable } from "../components/zone/ZoneTable";
import { ImportanceBarChart } from "../components/charts/ImportanceBarChart";
import { fmt, label } from "../lib/utils";

export interface OverviewPageProps {
  city: City | string;
  overview: CityOverview;
  data: ZoneFeatureCollection;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
  layer: string;
  onLayer: (layer: string) => void;
  navigate: (page: string) => void;
}

export function OverviewPage({
  overview: o,
  data,
  selected,
  onSelect,
  layer,
  onLayer,
  navigate,
}: OverviewPageProps) {
  return (
    <>
      <div className="metrics-grid">
        <MetricCard
          label="Area analyzed"
          value={fmt(o.area_km2, 0)}
          unit="km²"
          icon={MapIcon}
          detail={`${o.zone_count} geographical zones`}
        />
        <MetricCard
          label="Average surface heat"
          value={"+" + fmt(o.average_suhii)}
          unit="°C"
          icon={Thermometer}
          tone="orange"
          detail="SUHII · relative to rural reference"
        />
        <MetricCard
          label="Heat hotspots"
          value={o.hotspots}
          unit="zones"
          icon={Sun}
          tone="red"
          detail="Predicted SUHII ≥ 4°C"
        />
        <MetricCard
          label="Population in high-risk zones"
          value={fmt(o.population_exposed / 1000, 0)}
          unit="k"
          icon={Users}
          tone="blue"
          detail="Synthetic population · priority proxy"
        />
      </div>

      <div className="overview-main">
        <Card
          title="The city's heat landscape"
          subtitle="Explore patterns. Select a grid cell for a closer look."
          actions={
            <button
              type="button"
              className="text-button"
              onClick={() => navigate("Heat map")}
            >
              Explore map <ArrowUpRight size={15} />
            </button>
          }
        >
          <HeatMap
            data={data}
            selected={selected.id}
            onSelect={onSelect}
            layer={layer}
            onLayer={onLayer}
          />
          <div className="map-foot">
            <span>
              <span className="dot red" />
              {o.high_risk_zones} zones flagged as high risk
            </span>
            <span>Illustrative grid · WGS84</span>
          </div>
        </Card>

        <div className="insight-column">
          <section className="insight-card">
            <div className="insight-title">
              <Sparkles size={17} />
              <span>FROM THE EVIDENCE</span>
              <Badge tone="mint">MODEL INSIGHTS</Badge>
            </div>
            <h2>
              Every hotspot
              <br />
              has a story.
            </h2>
            <p>
              Your model identifies{" "}
              <strong>{label(o.importance[0]?.feature || "").toLowerCase()}</strong> as
              the strongest association with surface heat in this sample.
            </p>
            <div className="insight-divider" />
            <div className="insight-point">
              <span>
                <TreePine size={17} />
              </span>
              <div>
                <strong>Start with the landscape</strong>
                <p>
                  Explore vegetation and built-up surfaces alongside local model
                  contributions.
                </p>
              </div>
            </div>
            <div className="insight-point">
              <span>
                <Target size={17} />
              </span>
              <div>
                <strong>Focus where it matters</strong>
                <p>
                  {o.high_risk_zones} zones meet the demonstration high-priority
                  threshold.
                </p>
              </div>
            </div>
            <button type="button" onClick={() => navigate("Explainable AI")}>
              Understand the drivers <ArrowRight size={17} />
            </button>
          </section>

          <Card className="next-action">
            <div className="next-icon">
              <FlaskConical size={20} />
            </div>
            <div>
              <strong>What could a cooler city look like?</strong>
              <p>Test your next intervention.</p>
            </div>
            <button
              type="button"
              aria-label="Open intervention simulator"
              onClick={() => navigate("Intervention simulator")}
            >
              <ArrowUpRight size={20} />
            </button>
          </Card>
        </div>
      </div>

      <div className="overview-bottom">
        <Card
          title="Priority zones"
          subtitle="Ranked by the configured hazard × exposure × vulnerability score"
          actions={
            <button
              type="button"
              className="text-button"
              onClick={() => navigate("Heat risk")}
            >
              View all zones <ArrowRight size={14} />
            </button>
          }
        >
          <ZoneTable
            zones={o.priority_zones.slice(0, 5)}
            onSelect={(p: ZoneProperties) => {
              onSelect(p);
              navigate("Heat map");
            }}
          />
        </Card>

        <Card
          title="What's driving surface heat?"
          subtitle="Mean absolute SHAP contribution · °C"
          actions={<Network size={18} color="#7c8a83" />}
        >
          <ImportanceBarChart data={o.importance.slice(0, 5)} />
          <div className="chart-note">
            Model associations, not proof of causation.
            <button type="button" onClick={() => navigate("Explainable AI")}>
              Explore XAI <ArrowUpRight size={12} />
            </button>
          </div>
        </Card>
      </div>

      <Notice>
        This workspace uses synthetic environmental and demographic data. Live
        imports are stored separately. Predictions and intervention estimates
        are for method exploration, not operational planning.
      </Notice>
    </>
  );
}
