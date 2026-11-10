import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { MapPin, Target, Check } from "lucide-react";
import type { City, CityOverview, OptimizationResponse, ZoneAllocation, ZoneProperties } from "../types";
import { optimizationService } from "../services/optimizationService";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";
import { Pending } from "../components/common/Pending";
import { interventionNames } from "../lib/constants";
import { fmt } from "../lib/utils";

export interface OptimizerPageProps {
  city: City | string;
  overview: CityOverview;
  notify: (message: string) => void;
}

export function OptimizerPage({ city, overview, notify }: OptimizerPageProps) {
  const [water, setWater] = useState(1000);
  const [vegetation, setVegetation] = useState(40);
  const [land, setLand] = useState(100);
  const [minimum, setMinimum] = useState(0);

  const run = useMutation<OptimizationResponse>({
    mutationFn: () =>
      optimizationService.runOptimization({
        city: city as City,
        water_limit: water,
        max_vegetation_pct: vegetation,
        land_limit_pct: land,
        min_cooling: minimum,
      }),
    onSuccess: () => notify("Optimization run saved."),
  });

  return (
    <>
      <div className="sim-layout">
        <Card
          title="Set the boundaries"
          subtitle="OR-Tools CP-SAT · no budget objective"
        >
          <div className="form-body">
            <label>
              Total available water (m³/day)
              <input
                type="number"
                min="0"
                value={water}
                onChange={(e) => {
                  setWater(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label className="slider-label">
              <span>
                Maximum added vegetation<strong>{vegetation}%</strong>
              </span>
              <input
                type="range"
                min="0"
                max="60"
                value={vegetation}
                onChange={(e) => {
                  setVegetation(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label className="slider-label">
              <span>
                Use of available ground area<strong>{land}%</strong>
              </span>
              <input
                type="range"
                min="0"
                max="100"
                value={land}
                onChange={(e) => {
                  setLand(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <label>
              Minimum mean surface cooling (°C)
              <input
                type="number"
                min="0"
                max="4"
                step=".1"
                value={minimum}
                onChange={(e) => {
                  setMinimum(+e.target.value);
                  run.reset();
                }}
              />
            </label>
            <p className="muted">
              Analyzing the five highest-priority zones. The objective weights
              hypothetical cooling by heat, population, and elderly share.
            </p>
            <div className="mini-zone-list">
              {overview.priority_zones.slice(0, 5).map((p: ZoneProperties) => (
                <span key={p.id}>
                  <MapPin size={12} />
                  {p.name}
                </span>
              ))}
            </div>
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              <Target size={16} />
              {run.isPending
                ? "Finding a feasible plan…"
                : "Optimize interventions"}
            </Button>
          </div>
        </Card>

        <div className="stack">
          <Card
            title="Your intervention plan"
            subtitle="Feasible solutions backed by explicit constraints"
          >
            {run.isPending ? (
              <Pending message="Solving CP-SAT multi-zone discrete optimization…" />
            ) : run.isError ? (
              <Notice tone="warn">
                {run.error instanceof Error ? run.error.message : "Optimization failed"}
              </Notice>
            ) : run.data ? (
              run.data.feasible ? (
                <>
                  <div className="optimization-head">
                    <Badge tone="green">
                      <Check size={12} className="inline mr-1" />
                      {run.data.status}
                    </Badge>
                    <span>
                      {fmt(run.data.water_used, 0)} /{" "}
                      {fmt(run.data.water_available, 0)} m³ water/day
                    </span>
                  </div>
                  <div className="plan-metrics">
                    <div>
                      <strong>{fmt(run.data.mean_cooling, 2)}°C</strong>
                      <span>Mean hypothetical cooling</span>
                    </div>
                    <div>
                      <strong>
                        {fmt(run.data.population_in_selected_zones / 1000)}k
                      </strong>
                      <span>Population in selected zones</span>
                    </div>
                  </div>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>ZONE</th>
                          <th>INTERVENTIONS · COVERAGE</th>
                          <th>COOLING</th>
                        </tr>
                      </thead>
                      <tbody>
                        {run.data.selections.map((s: ZoneAllocation, idx: number) => (
                          <tr key={s.zone_id || idx}>
                            <td>{s.zone_name}</td>
                            <td>
                              {Object.entries(s.coverage).map(([k, v]) => (
                                <span className="block" key={k}>
                                  {interventionNames[k] || k} · {String(v)}%
                                </span>
                              ))}
                            </td>
                            <td>{fmt(s.estimated_cooling, 2)}°C</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="prose">
                    <p>{run.data.explanation}</p>
                  </div>
                </>
              ) : (
                <div className="form-body">
                  <Notice tone="warn">
                    No feasible plan found: {run.data.status}
                  </Notice>
                  {run.data.violations.map((s: string) => (
                    <p key={s}>{s}</p>
                  ))}
                </div>
              )
            ) : (
              <div className="empty">
                <Target size={40} />
                <h3>The right combination, within reach.</h3>
                <p>
                  Set practical limits and find a feasible
                  <br />
                  combination of cooling interventions.
                </p>
              </div>
            )}
          </Card>

          {run.data?.alternative?.feasible && (
            <Card
              title="An alternative with less water"
              subtitle="Same constraints; half the daily water allowance"
            >
              <div className="prose">
                <p>
                  <strong>{fmt(run.data.alternative.mean_cooling, 2)}°C</strong>{" "}
                  mean hypothetical cooling with{" "}
                  <strong>
                    {fmt(run.data.alternative.water_used, 0)} m³/day
                  </strong>
                  .
                </p>
              </div>
            </Card>
          )}

          <Notice>
            Population in selected zones is not “people protected.” The
            objective is a planning proxy. All intervention effects require
            local validation.
          </Notice>
        </div>
      </div>
    </>
  );
}
