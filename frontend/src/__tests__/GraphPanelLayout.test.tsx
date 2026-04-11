/**
 * Graph panel layout robustness regression tests.
 *
 * Protects against the "all agents in the bottom-left corner" bug where the
 * Cytoscape container ends up with clientHeight === 0 at the moment the
 * `cose` layout runs, collapsing every node to (0,0).
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-panel-layout-robustness
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GraphPanel from "@/components/graph/GraphPanel";

function renderPanel() {
  return render(
    <MemoryRouter>
      <GraphPanel />
    </MemoryRouter>,
  );
}

describe("GraphPanel — layout robustness (bottom-left bug)", () => {
  /** @spec 07_FRONTEND_SPEC.md#graph-panel-layout-robustness */
  it("cytoscape container uses inline width/height 100% (not `absolute inset-0` alone)", () => {
    const { container } = renderPanel();
    const cy = container.querySelector(
      '[data-testid="graph-cytoscape-container"]',
    ) as HTMLElement | null;
    expect(cy).not.toBeNull();

    // Inline styles must include width+height 100% so that cytoscape's own
    // container style mutation (which can interact badly with Tailwind's
    // `absolute inset-0` and collapse height to 0) cannot zero the height.
    const style = cy!.getAttribute("style") ?? "";
    expect(style).toMatch(/width:\s*100%/i);
    expect(style).toMatch(/height:\s*100%/i);
  });

  /** @spec 07_FRONTEND_SPEC.md#graph-panel-layout-robustness */
  it("exposes a stable test-id on the cytoscape container for E2E layout assertions", () => {
    const { getByTestId } = renderPanel();
    const cy = getByTestId("graph-cytoscape-container");
    expect(cy).toBeInTheDocument();
  });

  /** @spec 07_FRONTEND_SPEC.md#graph-panel-layout-robustness */
  it("panel root is position:relative so the absolutely-sized container anchors correctly", () => {
    const { getByTestId } = renderPanel();
    const panel = getByTestId("graph-panel");
    // Tailwind `relative` class must be present — otherwise the container's
    // `position:absolute` would anchor to the viewport instead of the panel
    // and Cytoscape's canvas would read the wrong dimensions.
    expect(panel.className).toMatch(/\brelative\b/);
  });
});
