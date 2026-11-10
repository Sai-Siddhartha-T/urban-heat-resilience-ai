import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SyntheticWarningBadge } from "../components/common/SyntheticWarningBadge";
import type { DatasetMetadata } from "../types/geojson";

describe("SyntheticWarningBadge Component", () => {
  const dummyMetadata: DatasetMetadata = {
    source: "Seeded synthetic demonstration dataset",
    synthetic: true,
    isSynthetic: true,
    city: "Ahmedabad",
    center: [23.02, 72.57],
    resolution_m: 1000,
    crs: "EPSG:4326",
    acquisition_date: "2025-05-15",
    rural_reference_c: 33,
    rural_method: "Configurable synthetic rural LST",
    generated_at: "2025-05-15T00:00:00+00:00",
    limitations: ["Synthetic environmental data"],
  };

  it("renders warning badge when metadata.isSynthetic is true", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge metadata={{ isSynthetic: true }} />
    );
    expect(html).toContain("synthetic-warning-badge");
    expect(html).toContain("Synthetic Fallback Data");
    expect(html).toContain('role="status"');
    expect(html).toContain('data-testid="synthetic-warning-badge"');
  });

  it("renders warning badge with full DatasetMetadata having isSynthetic: true", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge metadata={dummyMetadata} />
    );
    expect(html).toContain("synthetic-warning-badge");
    expect(html).toContain("Synthetic Fallback Data");
  });

  it("renders warning badge when fallback detection relies on metadata.synthetic", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge metadata={{ synthetic: true }} />
    );
    expect(html).toContain("synthetic-warning-badge");
    expect(html).toContain("Synthetic Fallback Data");
  });

  it("renders warning badge when source contains synthetic", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge metadata={{ source: "synthetic" }} />
    );
    expect(html).toContain("synthetic-warning-badge");
    expect(html).toContain("Synthetic Fallback Data");
  });

  it("renders warning badge when isSynthetic prop is passed directly as true", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge isSynthetic={true} />
    );
    expect(html).toContain("synthetic-warning-badge");
  });

  it("renders nothing (empty markup) when dataset is live / not synthetic", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge
        metadata={{
          source: "landsat",
          synthetic: false,
          isSynthetic: false,
        }}
      />
    );
    expect(html).toBe("");
  });

  it("renders nothing when isSynthetic prop is false", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge isSynthetic={false} />
    );
    expect(html).toBe("");
  });

  it("renders custom children content when provided", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge isSynthetic={true}>
        Custom Warning: Mock Data In Use
      </SyntheticWarningBadge>
    );
    expect(html).toContain("Custom Warning: Mock Data In Use");
    expect(html).not.toContain("Synthetic Fallback Data");
  });

  it("supports omitting the warning icon when showIcon is false", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge isSynthetic={true} showIcon={false}>
        No Icon Warning
      </SyntheticWarningBadge>
    );
    expect(html).toContain("No Icon Warning");
    expect(html).not.toContain("<svg");
  });

  it("applies custom class names properly", () => {
    const html = renderToStaticMarkup(
      <SyntheticWarningBadge isSynthetic={true} className="extra-badge-style" />
    );
    expect(html).toContain("synthetic-warning-badge");
    expect(html).toContain("extra-badge-style");
  });
});
