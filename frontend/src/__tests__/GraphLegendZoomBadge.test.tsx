/**
 * GraphLegend + ZoomTierBadge tests.
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-legend
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-zoom-tier-badge
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import GraphLegend from "@/components/graph/GraphLegend";
import ZoomTierBadge from "@/components/graph/ZoomTierBadge";
import { COMMUNITIES } from "@/config/constants";

describe("<GraphLegend />", () => {
  it("renders with all sections by default (open)", () => {
    render(<GraphLegend />);
    expect(screen.getByTestId("graph-legend")).toBeInTheDocument();
    expect(screen.getByTestId("graph-legend-content")).toBeInTheDocument();
    // Communities section lists every community from the config.
    // "Bridge" intentionally duplicates between the community list and
    // the edge list, so we use getAllByText there.
    for (const c of COMMUNITIES) {
      expect(screen.getAllByText(c.name).length).toBeGreaterThan(0);
    }
    // Node state + Edge sections
    expect(screen.getByText("Adopted")).toBeInTheDocument();
    expect(screen.getByText("Intra-community")).toBeInTheDocument();
  });

  it("collapses when the toggle is clicked", () => {
    render(<GraphLegend />);
    const toggle = screen.getByTestId("graph-legend-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(toggle);

    expect(
      screen.queryByTestId("graph-legend-content"),
    ).not.toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("re-opens on second click", () => {
    render(<GraphLegend />);
    const toggle = screen.getByTestId("graph-legend-toggle");
    fireEvent.click(toggle); // close
    fireEvent.click(toggle); // open
    expect(screen.getByTestId("graph-legend-content")).toBeInTheDocument();
  });
});

describe("<ZoomTierBadge />", () => {
  it("shows Close-up label for closeup tier", () => {
    render(<ZoomTierBadge tier="closeup" />);
    const badge = screen.getByTestId("zoom-tier-badge");
    expect(badge).toHaveAttribute("data-tier", "closeup");
    expect(screen.getByText("Close-up")).toBeInTheDocument();
  });

  it("shows Mid-range label for midrange tier", () => {
    render(<ZoomTierBadge tier="midrange" />);
    expect(screen.getByText("Mid-range")).toBeInTheDocument();
  });

  it("shows Overview label for overview tier", () => {
    render(<ZoomTierBadge tier="overview" />);
    expect(screen.getByText("Overview")).toBeInTheDocument();
  });

  it("updates data-tier attribute when tier changes", () => {
    const { rerender } = render(<ZoomTierBadge tier="overview" />);
    expect(screen.getByTestId("zoom-tier-badge")).toHaveAttribute(
      "data-tier",
      "overview",
    );
    rerender(<ZoomTierBadge tier="closeup" />);
    expect(screen.getByTestId("zoom-tier-badge")).toHaveAttribute(
      "data-tier",
      "closeup",
    );
  });
});
