import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, ArrowRight, ArrowDown, TreePine } from "lucide-react";
import type { City, SimulationResponse, ZoneFeatureCollection, ZoneProperties } from "../types";
import { simulationService } from "../services/simulationService";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";
import { Pending } from "../components/common/Pending";
import { ZonePicker } from "../components/zone/ZonePicker";
import { interventionNames } from "../lib/constants";
import { fmt } from "../lib/utils";

export interface SimulatorPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
  notify: (message: string) => void;
}

export function SimulatorPage({
  city,
  data,
  selected,
  onSelect,
  notify,
}: SimulatorPageProps) {
  const [coverage, setCoverage] = useState<Record<string, number>>({
    trees: 5,
    cool_roofs: 10,
  });
  const [name, setName] = useState("Greener streets");
  const [water, setWater] = useState(1000);

  const client = useQueryClient();

  const history = useQuery<SimulationResponse[]>({
    queryKey: ["scenarios", city],
    queryFn: () => simulationService.getSimulationHistory(city as City),
  });

  const run = useMutation<SimulationResponse>({
    mutationFn: () =>
      simulationService.runSimulation({
        city: city as City,
        zone_id: selected.id,
        name,
        coverage,
        water_limit: water,
        max_vegetation_pct: 40,
      }),
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ["scenarios", city] });
      notify(
        r.feasible
          ? "Scenario calculated and saved."
          : "Scenario saved with constraint violations.",
      );
    },
  });

  return (
    <>
      <div className="section-toolbar">
        <Notice>
          Hypothetical surface-cooling estimates. Coefficients are uncalibrated;
          ±40% is a sensitivity range.
        </Notice>
        <ZonePicker
          data={data}
          selected={selected}
          onSelect={(p: ZoneProperties) => {
            onSelect(p);
            run.reset();
          }}
        />
      </div>

      <div className="sim-layout">
        <Card
          title="Design your scenario"
          subtitle="Coverage is % of total zone area."
        >
          <div className="form-body">
            <label>
              Scenario name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={80}
              />
            </label>
            <div className="constraint-summary">
              <span>
                Land <b>{fmt(selected.available_land_pct, 0)}%</b>
              </span>
              <span>
                Roofs <b>{fmt(selected.roof_pct, 0)}%</b>
              </span>
              <span>
                Roads <b>{fmt(selected.road_pct, 0)}%</b>
              </span>
            </div>

            {Object.entries(interventionNames).map(([key, title]) => (
              <label className="slider-label compact" key={key}>
                <span>
                  {title}
                  <strong>{coverage[key] || 0}%</strong>
                </span>
                <input
                  type="range"
                  aria-label={title + " coverage"}
                  min="0"
                  max="60"
                  step="5"
                  value={coverage[key] || 0}
                  onChange={(e) => {
                    setCoverage({ ...coverage, [key]: Number(e.target.value) });
                    run.reset();
                  }}
                />
              </label>
            ))}

            <label>
              Available water (m³/day)
              <input
                type="number"
                min="0"
                value={water}
                onChange={(e) => {
                  setWater(Number(e.target.value));
                  run.reset();
                }}
              />
            </label>

            <Button
              onClick={() => run.mutate()}
              disabled={run.isPending || !name.trim()}
            >
              <FlaskConical size={16} />
              {run.isPending ? "Simulating…" : "Run & save scenario"}
            </Button>
          </div>
        </Card>

        <div className="stack">
          <Card title="Before & after" subtitle={selected.name}>
            {run.isError ? (
              <Notice tone="warn">
                {run.error instanceof Error ? run.error.message : "Simulation failed"}
              </Notice>
            ) : run.isPending ? (
              <Pending message="Evaluating thermal impact & physical feasibility…" />
            ) : run.data ? (
              run.data.feasible ? (
                <div className="scenario-result">
                  <Badge tone="green">Feasible under supplied constraints</Badge>
                  <div className="comparison">
                    <div>
                      <span>Current SUHII</span>
                      <strong>+{fmt(run.data.before_suhii)}°C</strong>
                    </div>
                    <ArrowRight />
                    <div className="after">
                      <span>Scenario SUHII</span>
                      <strong>{fmt(run.data.after_suhii)}°C</strong>
                    </div>
                  </div>
                  <div className="cooling-impact">
                    <ArrowDown size={22} />
                    <strong>{fmt(run.data.estimated_cooling, 2)}°C</strong>
                    <span>hypothetical surface cooling</span>
                  </div>
                  <p>
                    Sensitivity range:{" "}
                    {run.data.sensitivity_range
                      ? run.data.sensitivity_range.map((n: number) => fmt(n, 2)).join("–")
                      : "—"}
                    °C
                  </p>
                  <p>
                    Water requirement: {fmt(run.data.water_m3_day, 0)} m³/day
                  </p>
                </div>
              ) : (
                <div className="form-body">
                  <Notice tone="warn">
                    Scenario is infeasible. No cooling result is claimed.
                  </Notice>
                  {run.data.violations.map((v: string) => (
                    <p key={v}>{v}</p>
                  ))}
                </div>
              )
            ) : (
              <div className="empty">
                <TreePine size={36} />
                <h3>A small change. A different possibility.</h3>
                <p>
                  Choose coverage, then run your scenario
                  <br />
                  to calculate effects and check feasibility.
                </p>
              </div>
            )}
          </Card>

          <Card
            title="Scenario comparison"
            subtitle="Saved runs from this city"
          >
            {history.data?.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>SCENARIO</th>
                      <th>COOLING</th>
                      <th>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.data.slice(0, 8).map((s: SimulationResponse, idx: number) => (
                      <tr key={s.id || idx}>
                        <td>
                          {s.name}
                          <small className="block muted">{s.zone_id}</small>
                        </td>
                        <td>
                          {s.feasible
                            ? fmt(s.estimated_cooling, 2) + "°C"
                            : "—"}
                        </td>
                        <td>
                          <Badge tone={s.feasible ? "green" : "red"}>
                            {s.feasible ? "Feasible" : "Infeasible"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty small">
                Your saved scenarios will appear here.
              </div>
            )}
          </Card>

          <Notice>
            Ground area is shared by trees, parks, vegetation, corridors, and
            water. Roof treatments are mutually exclusive. Protected zones
            exclude ground interventions.
          </Notice>
        </div>
      </div>
    </>
  );
}
