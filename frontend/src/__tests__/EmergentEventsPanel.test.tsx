/**
 * EmergentEventsPanel tests — filter, sort, render.
 * @spec docs/spec/07_FRONTEND_SPEC.md#emergent-events-panel
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";

import EmergentEventsPanel from "@/components/emergent/EmergentEventsPanel";
import {
  filterAndSortEvents,
  severityToWidth,
} from "@/components/emergent/emergentEventsUtils";
import { useSimulationStore } from "@/store/simulationStore";
import type { EmergentEvent } from "@/types/simulation";

function ev(overrides: Partial<EmergentEvent>): EmergentEvent {
  return {
    event_type: "viral_cascade",
    step: 1,
    community_id: null,
    severity: 0.5,
    description: "Test event",
    ...overrides,
  };
}

// --------------------------------------------------------------------------- //
// Pure helpers                                                                //
// --------------------------------------------------------------------------- //

describe("severityToWidth", () => {
  it("clamps severity > 1 to 100%", () => {
    expect(severityToWidth(2.5)).toBe("100%");
  });
  it("clamps negative severity to 0%", () => {
    expect(severityToWidth(-0.1)).toBe("0%");
  });
  it("renders a fractional severity as a rounded percentage", () => {
    expect(severityToWidth(0.625)).toBe("63%");
  });
});

describe("filterAndSortEvents", () => {
  const events = [
    ev({ event_type: "viral_cascade", step: 3 }),
    ev({ event_type: "polarization", step: 5 }),
    ev({ event_type: "viral_cascade", step: 1 }),
    ev({ event_type: "echo_chamber", step: 4 }),
  ];

  it("returns all events when filter is 'all'", () => {
    expect(filterAndSortEvents(events, "all")).toHaveLength(4);
  });

  it("sorts by descending step number", () => {
    const sorted = filterAndSortEvents(events, "all");
    expect(sorted.map((e) => e.step)).toEqual([5, 4, 3, 1]);
  });

  it("filters by a single event type", () => {
    const cascades = filterAndSortEvents(events, "viral_cascade");
    expect(cascades).toHaveLength(2);
    expect(cascades.every((e) => e.event_type === "viral_cascade")).toBe(true);
  });

  it("returns an empty array when no events match filter", () => {
    expect(filterAndSortEvents(events, "collapse")).toEqual([]);
  });
});

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

describe("<EmergentEventsPanel />", () => {
  beforeEach(() => {
    useSimulationStore.setState({ emergentEvents: [] });
  });

  it("shows the empty state when no events exist", () => {
    render(<EmergentEventsPanel />);
    expect(screen.getByTestId("emergent-events-empty")).toBeInTheDocument();
    expect(screen.getByText(/No emergent events yet/i)).toBeInTheDocument();
  });

  it("renders event rows with severity bars", () => {
    useSimulationStore.setState({
      emergentEvents: [
        ev({ event_type: "viral_cascade", step: 10, severity: 0.8 }),
        ev({ event_type: "polarization", step: 12, severity: 0.6 }),
      ],
    });
    render(<EmergentEventsPanel />);
    expect(screen.getByTestId("emergent-events-list")).toBeInTheDocument();
    // Most recent step first (step 12)
    expect(
      screen.getByTestId("emergent-event-row-12-polarization"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("emergent-event-row-10-viral_cascade"),
    ).toBeInTheDocument();
  });

  it("filters events when a filter button is clicked", () => {
    useSimulationStore.setState({
      emergentEvents: [
        ev({ event_type: "viral_cascade", step: 1 }),
        ev({ event_type: "polarization", step: 2 }),
      ],
    });
    render(<EmergentEventsPanel />);

    fireEvent.click(screen.getByTestId("emergent-filter-polarization"));

    // Only the polarization row should remain
    expect(
      screen.queryByTestId("emergent-event-row-1-viral_cascade"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("emergent-event-row-2-polarization"),
    ).toBeInTheDocument();
  });

  it("shows the header count badge", () => {
    useSimulationStore.setState({
      emergentEvents: [
        ev({ step: 1 }),
        ev({ step: 2 }),
        ev({ step: 3 }),
      ],
    });
    render(<EmergentEventsPanel />);
    expect(screen.getByText(/3 detected/)).toBeInTheDocument();
  });
});
