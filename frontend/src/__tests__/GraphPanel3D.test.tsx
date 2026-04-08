/**
 * GraphPanel 3D contract regression tests.
 *
 * Locks in the visual + interaction contract from
 * 18_FRONTEND_PERFORMANCE_SPEC §5.
 *
 * NOTE: three.js WebGL itself is not exercisable in jsdom, so these tests
 * focus on the DOM-level contract: correct test-ids, inline sizing, color
 * palette sharing with the Communities legend, and the controls hint text.
 * Frame-rate SPEC items (G3D-AC-01/02) are verified via Playwright.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GraphPanel from "@/components/graph/GraphPanel";
import { COMMUNITIES } from "@/config/constants";

// react-force-graph-3d pulls in three.js which tries to use WebGL at import
// time in jsdom. Stub it with a no-op component so the tests can mount.
vi.mock("react-force-graph-3d", () => ({
  __esModule: true,
  default: () => null,
}));

function renderPanel() {
  return render(
    <MemoryRouter>
      <GraphPanel />
    </MemoryRouter>,
  );
}

describe("GraphPanel 3D — visual contract", () => {
  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#5-graph-3d-rendering */
  it("root panel has the 3D aria label (not the legacy 2D label)", () => {
    const { getByTestId } = renderPanel();
    const panel = getByTestId("graph-panel");
    expect(panel.getAttribute("aria-label")).toMatch(/3D/i);
    expect(panel.getAttribute("aria-label")).toMatch(/social network/i);
  });

  /** @spec G3D-09 — layout robustness (bottom-left bug) */
  it("WebGL container uses inline width/height 100% (not absolute inset-0 alone)", () => {
    const { getByTestId } = renderPanel();
    const cy = getByTestId("graph-cytoscape-container");
    const style = cy.getAttribute("style") ?? "";
    expect(style).toMatch(/width:\s*100%/i);
    expect(style).toMatch(/height:\s*100%/i);
    expect(style).toMatch(/position:\s*absolute/i);
  });

  /** @spec G3D-09 — anchor element must be position:relative */
  it("panel root is position:relative so the absolutely-sized container anchors correctly", () => {
    const { getByTestId } = renderPanel();
    const panel = getByTestId("graph-panel");
    expect(panel.className).toMatch(/\brelative\b/);
  });

  /** @spec G3D-AC-03 — community palette single source of truth */
  it("references the COMMUNITIES palette from config (legend + graph share colors)", () => {
    // Smoke: COMMUNITIES must be non-empty and each entry must have a hex color.
    // The graph component imports from the same module and derives both its
    // node color map and the hover-tooltip labels from it.
    expect(COMMUNITIES.length).toBeGreaterThan(0);
    for (const c of COMMUNITIES) {
      expect(c.color).toMatch(/^#[0-9a-f]{6}$/i);
    }
    // And the panel renders without throwing against that palette.
    const { getByTestId } = renderPanel();
    expect(getByTestId("graph-panel")).toBeInTheDocument();
  });

  /** @spec G3D-AC-05 — controls hint text */
  it("displays the 3D controls hint (left-drag / scroll / right-drag)", () => {
    const { getByText } = renderPanel();
    expect(getByText(/Left-drag/i)).toBeInTheDocument();
    expect(getByText(/Left-drag/i).textContent).toMatch(/rotate/i);
    expect(getByText(/Left-drag/i).textContent).toMatch(/zoom/i);
    expect(getByText(/Left-drag/i).textContent).toMatch(/pan/i);
  });
});
