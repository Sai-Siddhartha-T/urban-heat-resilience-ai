import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FileText, ArrowDownToLine } from "lucide-react";
import type { City, CityOverview, DataStatusResponse, ReportGenerateResponse } from "../types";
import { reportService } from "../services/reportService";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";

export interface ReportsPageProps {
  city: City | string;
  overview: CityOverview;
  status?: DataStatusResponse;
  notify: (message: string) => void;
}

export function ReportsPage({
  city,
  overview,
  status,
  notify,
}: ReportsPageProps) {
  const [report, setReport] = useState<ReportGenerateResponse | null>(null);

  const create = useMutation<ReportGenerateResponse>({
    mutationFn: () => reportService.generateReport(city as City),
    onSuccess: (r) => {
      setReport(r);
      notify("Report generated from current analysis.");
    },
  });

  const save = async (url: string, name: string) => {
    try {
      await reportService.downloadFile(url, name);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Download failed";
      notify(message);
    }
  };

  return (
    <>
      <div className="report-banner">
        <div>
          <div className="eyebrow">FROM ANALYSIS TO ACTION</div>
          <h2>
            Your city's evidence,
            <br />
            ready to share.
          </h2>
          <p>
            A reproducible snapshot of model results, scenarios,
            <br />
            constraints, sources, and limitations.
          </p>
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            <FileText size={16} />
            {create.isPending ? "Generating…" : "Generate analysis report"}
          </Button>
        </div>
        <div className="report-illustration">
          <FileText size={85} strokeWidth={1} />
          <span>
            HEATWISE
            <br />
            <strong>{city}</strong>
            <small>URBAN HEAT ANALYSIS</small>
          </span>
          <Badge>SYNTHETIC DEMONSTRATION</Badge>
        </div>
      </div>

      {create.isError && (
        <Notice tone="warn">
          {create.error instanceof Error ? create.error.message : "Generation failed"}
        </Notice>
      )}

      {report && (
        <div className="download-grid">
          {[
            {
              key: "markdown_url" as const,
              title: "Readable report",
              desc: "Markdown · methods & results",
              ext: "md",
            },
            {
              key: "csv_url" as const,
              title: "Zone-level data",
              desc: "CSV · predictions & risk",
              ext: "csv",
            },
            {
              key: "download_url" as const,
              title: "Complete analysis",
              desc: "JSON · all evidence",
              ext: "json",
            },
          ].map(({ key, title, desc, ext }) => (
            <Card key={key}>
              <div className="download-card">
                <FileText />
                <h3>{title}</h3>
                <p>{desc}</p>
                <Button
                  variant="outline"
                  onClick={() => save(report[key], "heatwise-report." + ext)}
                >
                  <ArrowDownToLine size={15} />
                  Download {ext.toUpperCase()}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="two-columns">
        <Card
          title="Methodology & provenance"
          subtitle="Reproduce the result, understand its limits"
        >
          <div className="prose">
            <p>
              <strong>Surface heat:</strong> SUHII = urban land surface
              temperature − rural reference land surface temperature. Current
              reference: {overview.metadata.rural_reference_c}°C, synthetic.
            </p>
            <p>
              <strong>Dataset:</strong> seeded synthetic grid,{" "}
              {overview.zone_count} cells. The acquisition date is a
              demonstration label. Live imports never silently replace the
              sample.
            </p>
            <p>
              <strong>Prediction:</strong> three tree ensembles; spatial
              train/validation/buffer/test split. Actual TreeSHAP explanations.
            </p>
            <p>
              <strong>Interventions:</strong> independent hypothetical
              coefficients. No conversion of SHAP values into cooling estimates.
            </p>
            <p>
              <strong>Optimization:</strong> CP-SAT with 5% coverage increments,
              water, surface capacity, compatibility, protection, and vegetation
              constraints. No cost objective.
            </p>
          </div>
        </Card>

        <Card
          title="Connection status"
          subtitle="Configuration is not proof of successful access"
        >
          <div className="prose">
            <div className="source-row">
              <span>Database</span>
              <Badge tone="neutral">{status?.database || "Loading"}</Badge>
            </div>
            {(["groq", "gemini"] as const).map((p) => (
              <div className="source-row" key={p}>
                <span>{p === "groq" ? "Groq" : "Google Gemini"}</span>
                <Badge
                  tone={status?.providers?.[p]?.availability === "verified" ? "green" : "orange"}
                >
                  {status?.providers?.[p]?.availability === "verified"
                    ? "Latest request verified"
                    : status?.providers?.[p]?.availability === "failed"
                      ? "Latest request failed"
                      : status?.providers?.[p]?.configured
                        ? "Configured · not verified"
                        : "Needs key & model"}
                </Badge>
              </div>
            ))}
            <div className="source-row">
              <span>Google Earth Engine</span>
              <Badge
                tone={status?.earth_engine?.latest_success ? "green" : "orange"}
              >
                {status?.earth_engine?.latest_success
                  ? "Latest retrieval verified"
                  : status?.earth_engine?.configured
                    ? "Configured · not verified"
                    : "Needs project configuration"}
              </Badge>
            </div>
            <Notice>
              A configured key is not a connection. Provider status turns
              verified only after a successful request; failed requests remain
              visible with their latest attempt timestamp.
            </Notice>
          </div>
        </Card>
      </div>
    </>
  );
}
