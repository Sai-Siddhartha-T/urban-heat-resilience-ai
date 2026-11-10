import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NormalModeContent, resolveNormalModeView } from "../pages/NormalModeContent";
import type { WorkspaceResponse } from "../types";

vi.mock("../pages/EvidenceWorkspacePage", () => ({
  EvidenceWorkspacePage: () => <div>Evidence workspace view</div>,
}));

const unavailableWorkspace: WorkspaceResponse = {
  schema_version: "1",
  city: "Ahmedabad",
  center: [23.0225, 72.5714],
  mode: "normal",
  analysis: {
    status: "unavailable",
    reason: "No verified observations",
    synthetic: false,
    dataset_id: null,
  },
  assets: [],
  layers: [],
  capabilities: {},
  limitations: [],
};

describe("normal-mode evidence gate", () => {
  it("uses the evidence workspace even when legacy analysis data might exist", () => {
    expect(resolveNormalModeView(unavailableWorkspace, false)).toBe("evidence");
    const html = renderToStaticMarkup(
      <NormalModeContent
        city="Ahmedabad"
        workspace={unavailableWorkspace}
        isLoading={false}
        onOpenData={vi.fn()}
      >
        <div>Legacy analysis</div>
      </NormalModeContent>,
    );
    expect(html).toContain("Evidence workspace view");
    expect(html).not.toContain("Legacy analysis");
  });

  it("surfaces evidence workspace request failures", () => {
    expect(resolveNormalModeView(undefined, false, "Request failed")).toBe("error");
    const html = renderToStaticMarkup(
      <NormalModeContent
        city="Ahmedabad"
        isLoading={false}
        error="Request failed"
        onOpenData={vi.fn()}
      >
        <div>Legacy analysis</div>
      </NormalModeContent>,
    );
    expect(html).toContain("Evidence workspace unavailable: Request failed");
    expect(html).not.toContain("Legacy analysis");
  });

  it("renders legacy analytical pages only after workspace analysis is available", () => {
    const workspace = {
      ...unavailableWorkspace,
      analysis: { ...unavailableWorkspace.analysis, status: "available" as const },
    };
    expect(resolveNormalModeView(workspace, false)).toBe("analysis");
    const html = renderToStaticMarkup(
      <NormalModeContent
        city="Ahmedabad"
        workspace={workspace}
        isLoading={false}
        onOpenData={vi.fn()}
      >
        <div>Validated analysis</div>
      </NormalModeContent>,
    );
    expect(html).toContain("Validated analysis");
  });
});
