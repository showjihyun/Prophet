/**
 * FormProgressBanner tests — progress math, quick-start toggle, missing-field
 * checklist, a11y attributes.
 * @spec docs/spec/07_FRONTEND_SPEC.md#campaign-form-progress
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import FormProgressBanner from "@/components/campaign/FormProgressBanner";

describe("<FormProgressBanner />", () => {
  it("shows 0/N when no fields are satisfied", () => {
    render(
      <FormProgressBanner
        fields={[
          { label: "Project", satisfied: false },
          { label: "Name", satisfied: false },
          { label: "Message", satisfied: false },
        ]}
        quickStart={false}
        onToggleQuickStart={vi.fn()}
      />,
    );
    expect(screen.getByTestId("form-progress-count")).toHaveTextContent(
      "0 / 3 required fields",
    );
    // Progress bar width = 0%
    const fill = screen.getByTestId("form-progress-bar-fill");
    expect(fill).toHaveStyle({ width: "0%" });
  });

  it("lists missing required fields", () => {
    render(
      <FormProgressBanner
        fields={[
          { label: "Project", satisfied: true },
          { label: "Name", satisfied: false },
          { label: "Message", satisfied: false },
        ]}
        quickStart={false}
        onToggleQuickStart={vi.fn()}
      />,
    );
    const missing = screen.getByTestId("form-progress-missing");
    expect(missing).toHaveTextContent("Name");
    expect(missing).toHaveTextContent("Message");
    // "Project" is satisfied, should NOT be in the missing list
    expect(missing).not.toHaveTextContent("Project");
  });

  it("shows complete state when all fields are satisfied", () => {
    render(
      <FormProgressBanner
        fields={[
          { label: "Project", satisfied: true },
          { label: "Name", satisfied: true },
        ]}
        quickStart={false}
        onToggleQuickStart={vi.fn()}
      />,
    );
    expect(screen.getByTestId("form-progress-complete")).toBeInTheDocument();
    // No missing list when everything is done
    expect(
      screen.queryByTestId("form-progress-missing"),
    ).not.toBeInTheDocument();
    // Progress bar at 100%
    const fill = screen.getByTestId("form-progress-bar-fill");
    expect(fill).toHaveStyle({ width: "100%" });
  });

  it("toggles quick-start when the button is clicked", () => {
    const toggle = vi.fn();
    render(
      <FormProgressBanner
        fields={[{ label: "Project", satisfied: false }]}
        quickStart={false}
        onToggleQuickStart={toggle}
      />,
    );
    fireEvent.click(screen.getByTestId("quick-start-toggle"));
    expect(toggle).toHaveBeenCalledTimes(1);
  });

  it("reflects quick-start state in the button label and aria-pressed", () => {
    render(
      <FormProgressBanner
        fields={[{ label: "Project", satisfied: true }]}
        quickStart={true}
        onToggleQuickStart={vi.fn()}
      />,
    );
    const btn = screen.getByTestId("quick-start-toggle");
    expect(btn).toHaveAttribute("aria-pressed", "true");
    expect(btn).toHaveTextContent(/Quick Start ON/);
  });

  it("sets progressbar aria values", () => {
    render(
      <FormProgressBanner
        fields={[
          { label: "A", satisfied: true },
          { label: "B", satisfied: true },
          { label: "C", satisfied: false },
          { label: "D", satisfied: false },
        ]}
        quickStart={false}
        onToggleQuickStart={vi.fn()}
      />,
    );
    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toHaveAttribute("aria-valuenow", "50");
    expect(progressbar).toHaveAttribute("aria-valuemin", "0");
    expect(progressbar).toHaveAttribute("aria-valuemax", "100");
  });
});
