import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Button } from "../components/button";

describe("Button Primitive Component", () => {
  it("renders with default primary variant and btn class", () => {
    const html = renderToStaticMarkup(<Button>Execute Simulation</Button>);
    expect(html).toContain("btn");
    expect(html).toContain("btn-primary");
    expect(html).toContain("Execute Simulation");
  });

  it("renders with outline variant class when specified", () => {
    const html = renderToStaticMarkup(<Button variant="outline">Export Report</Button>);
    expect(html).toContain("btn-outline");
    expect(html).toContain("Export Report");
  });

  it("renders with ghost variant class when specified", () => {
    const html = renderToStaticMarkup(<Button variant="ghost">Dismiss</Button>);
    expect(html).toContain("btn-ghost");
  });

  it("applies custom className alongside variant classes", () => {
    const html = renderToStaticMarkup(
      <Button variant="outline" className="extra-class custom-padding">
        Action
      </Button>,
    );
    expect(html).toContain("btn-outline");
    expect(html).toContain("extra-class");
    expect(html).toContain("custom-padding");
  });

  it("renders disabled attribute when disabled prop is true", () => {
    const html = renderToStaticMarkup(<Button disabled>Disabled Action</Button>);
    expect(html).toContain("disabled");
  });
});
