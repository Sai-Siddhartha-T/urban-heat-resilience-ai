import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import type { City, RiskAnalysisResponse, VulnerabilityBreakdown, ZoneFeature, ZoneFeatureCollection, ZoneProperties } from "../types";
import { riskService } from "../services/riskService";
import { Card } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";
import { ZoneTable } from "../components/zone/ZoneTable";
import { fmt } from "../lib/utils";

export interface RiskPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
}

export function RiskPage({ city, data, selected, onSelect }: RiskPageProps) {
  const [weights, setWeights] = useState<[number, number, number]>([1, 1, 1]);
  const [query, setQuery] = useState("");

  const run = useMutation<RiskAnalysisResponse>({
    mutationFn: () =>
      riskService.analyzeRisk({
        city: city as City,
        hazard_weight: weights[0],
        exposure_weight: weights[1],
        vulnerability_weight: weights[2],
      }),
  });

  const scores = new globalThis.Map<string, VulnerabilityBreakdown>(
    (run.data?.zones || []).map((z) => [z.zone_id, z]),
  );

  const zones: ZoneProperties[] = data.features
    .map((f: ZoneFeature) => {
      const breakdown = scores.get(f.properties.id);
      if (breakdown) {
        return {
          ...f.properties,
          risk_score: breakdown.risk_score,
          hazard: breakdown.hazard,
          exposure: breakdown.exposure,
          vulnerability: breakdown.vulnerability,
          risk_level: breakdown.risk_level,
        };
      }
      return f.properties;
    })
    .filter((p: ZoneProperties) => p.name.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => b.risk_score - a.risk_score);

  return (
    <>
      <div className="two-columns risk-layout">
        <Card
          title="Make priorities explicit"
          subtitle="Configure the exponents in the risk framework."
        >
          <div className="equation">
            Risk = Hazard<sup>wH</sup> × Exposure<sup>wE</sup> × Vulnerability
            <sup>wV</sup>
          </div>
          <div className="form-body">
            {(["Hazard", "Exposure", "Vulnerability"] as const).map((name, i) => (
              <label className="slider-label" key={name}>
                <span>
                  {name} exponent <strong>{weights[i].toFixed(1)}</strong>
                </span>
                <input
                  aria-label={name + " weight"}
                  type="range"
                  min="0.1"
                  max="3"
                  step="0.1"
                  value={weights[i]}
                  onChange={(e) => {
                    const nextVal = Number(e.target.value);
                    setWeights((prev) => {
                      const next = [...prev] as [number, number, number];
                      next[i] = nextVal;
                      return next;
                    });
                  }}
                />
              </label>
            ))}
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              {run.isPending ? "Calculating…" : "Recalculate priorities"}
            </Button>
            {run.isError && (
              <Notice tone="warn">
                {run.error instanceof Error ? run.error.message : "Calculation failed"}
              </Notice>
            )}
          </div>
        </Card>

        <Card
          title="What the score can tell you"
          subtitle="Transparent inputs, visible gaps"
        >
          <div className="prose">
            <p>
              <strong>Hazard:</strong> predicted SUHII divided by 8°C.
            </p>
            <p>
              <strong>Exposure:</strong> population density divided by 25,000
              people/km².
            </p>
            <p>
              <strong>Vulnerability:</strong> synthetic elderly share divided by
              25%. Population density is not used as vulnerability.
            </p>
            <p>
              Each component is clipped to [0, 1], raised to its configured
              exponent, multiplied, then scaled to 100. High ≥20; moderate ≥8.
            </p>
            <Notice>
              Socioeconomic conditions, health data, and access to cooling are
              unavailable. This is a screening proxy, not a health-risk
              forecast.
            </Notice>
          </div>
        </Card>
      </div>

      <Card
        title="Zone priorities"
        subtitle={`${zones.length} zones · ${run.data ? "Recalculated" : "Default"} framework`}
        actions={
          <div className="search-box">
            <Search size={15} />
            <input
              placeholder="Find a sector…"
              aria-label="Search zones"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        }
      >
        <ZoneTable zones={zones.slice(0, 40)} onSelect={onSelect} />
      </Card>

      <div className="selected-summary">
        Selected: {selected.name} · Risk score{" "}
        {fmt(
          scores.get(selected.id)?.risk_score ?? selected.risk_score,
        )}
      </div>
    </>
  );
}
