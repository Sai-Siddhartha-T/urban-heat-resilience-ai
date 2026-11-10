import React from "react";
import type { City } from "../types";
import type { WorkspaceResponse } from "../types";
import { EvidenceWorkspacePage } from "./EvidenceWorkspacePage";
import { NoAnalysisState } from "../components/common/NoAnalysisState";
import { Pending } from "../components/common/Pending";

export type NormalModeView = "loading" | "error" | "evidence" | "analysis";

export function resolveNormalModeView(
  workspace: WorkspaceResponse | undefined,
  isLoading: boolean,
  error?: string,
): NormalModeView {
  if (isLoading) return "loading";
  if (error) return "error";
  if (!workspace) return "loading";
  return workspace.analysis.status === "unavailable" ? "evidence" : "analysis";
}

export interface NormalModeContentProps {
  city: City;
  workspace?: WorkspaceResponse;
  isLoading: boolean;
  error?: string;
  onOpenData: () => void;
  children: React.ReactNode;
}

export function NormalModeContent({
  city,
  workspace,
  isLoading,
  error,
  onOpenData,
  children,
}: NormalModeContentProps) {
  const view = resolveNormalModeView(workspace, isLoading, error);

  if (view === "loading") {
    return <Pending message={`Checking acquired evidence for ${city}…`} />;
  }
  if (view === "error") {
    return (
      <NoAnalysisState
        onOpenData={onOpenData}
        message={`Evidence workspace unavailable: ${error}`}
      />
    );
  }
  if (view === "evidence" && workspace) {
    return <EvidenceWorkspacePage key={city} city={city} workspace={workspace} />;
  }
  return <>{children}</>;
}
