import React from "react";
import { Database, TriangleAlert } from "lucide-react";
import { Button } from "./Button";

export interface NoAnalysisStateProps {
  message?: string;
  onOpenData: () => void;
}

/** Truthful normal-mode state: evidence may exist, but no analysis is fabricated. */
export function NoAnalysisState({ message, onOpenData }: NoAnalysisStateProps) {
  return (
    <section className="empty" data-testid="no-analysis-state">
      <TriangleAlert size={40} />
      <h2>No validated heat analysis is available</h2>
      <p>
        Heatwise will not generate a map, heat score, or recommendation from
        missing data. Ingest evidence to inspect its provenance, or explicitly
        select Demo Mode for labelled software demonstration data.
      </p>
      {message && <p className="muted">{message}</p>}
      <Button onClick={onOpenData}>
        <Database size={16} /> Open data sources
      </Button>
    </section>
  );
}
