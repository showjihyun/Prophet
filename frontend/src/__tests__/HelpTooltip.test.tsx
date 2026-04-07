/**
 * HelpTooltip — unit tests for the shared contextual help component.
 *
 * Covers:
 * - Glossary term lookup vs inline label/text
 * - Hover open/close
 * - Click toggle (sticky)
 * - Outside click closes the popover
 * - Alignment classes
 * - Defensive: no content → renders nothing
 * - aria-label includes the resolved label
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HelpTooltip from "@/components/shared/HelpTooltip";

describe("HelpTooltip", () => {
  describe("content resolution", () => {
    it("uses glossary term when provided", () => {
      render(<HelpTooltip term="polarization" />);
      // Tooltip popover is always rendered (opacity-toggled), so its text
      // is in the DOM regardless of visibility.
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent("Polarization Index");
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent(/divided/i);
    });

    it("uses inline label/text when no term given", () => {
      render(<HelpTooltip label="Custom" text="My explanation." />);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent("Custom");
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveTextContent("My explanation.");
    });

    it("renders nothing when no content is provided", () => {
      const { container } = render(<HelpTooltip />);
      expect(container.firstChild).toBeNull();
    });

    it("includes the label in the button aria-label", () => {
      render(<HelpTooltip term="influencer" />);
      expect(
        screen.getByRole("button", { name: /Influencer/i }),
      ).toBeInTheDocument();
    });
  });

  describe("hover behavior", () => {
    it("starts hidden (opacity-0)", () => {
      render(<HelpTooltip term="polarization" />);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-0");
    });

    it("becomes visible on mouse enter", () => {
      render(<HelpTooltip term="polarization" />);
      const wrapper = screen.getByRole("button").parentElement!;
      fireEvent.mouseEnter(wrapper);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-100");
    });

    it("hides on mouse leave", () => {
      render(<HelpTooltip term="polarization" />);
      const wrapper = screen.getByRole("button").parentElement!;
      fireEvent.mouseEnter(wrapper);
      fireEvent.mouseLeave(wrapper);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-0");
    });
  });

  describe("click behavior (sticky popover)", () => {
    it("toggles open on button click", () => {
      render(<HelpTooltip term="polarization" />);
      const button = screen.getByRole("button");
      fireEvent.click(button);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-100");
    });

    it("closes on second click", () => {
      render(<HelpTooltip term="polarization" />);
      const button = screen.getByRole("button");
      fireEvent.click(button);
      fireEvent.click(button);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-0");
    });

    it("closes when clicking outside the wrapper", () => {
      render(
        <div>
          <HelpTooltip term="polarization" />
          <button data-testid="outside">outside</button>
        </div>,
      );
      const helpButton = screen.getByRole("button", { name: /Polarization/i });
      fireEvent.click(helpButton);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-100");
      // Simulate outside mousedown
      fireEvent.mouseDown(screen.getByTestId("outside"));
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("opacity-0");
    });
  });

  describe("alignment", () => {
    it("centers by default", () => {
      render(<HelpTooltip term="polarization" />);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("left-1/2");
    });

    it("aligns right when align='right'", () => {
      render(<HelpTooltip term="polarization" align="right" />);
      const tooltip = screen.getByRole("tooltip", { hidden: true });
      expect(tooltip).toHaveClass("right-0");
      expect(tooltip).not.toHaveClass("left-1/2");
    });

    it("aligns left when align='left'", () => {
      render(<HelpTooltip term="polarization" align="left" />);
      const tooltip = screen.getByRole("tooltip", { hidden: true });
      expect(tooltip).toHaveClass("left-0");
      expect(tooltip).not.toHaveClass("left-1/2");
    });
  });

  describe("anti-flicker invariants", () => {
    it("tooltip is always present in DOM (not conditionally mounted)", () => {
      // This is the core anti-flicker design — opacity toggling, not mount/unmount.
      render(<HelpTooltip term="polarization" />);
      expect(screen.getByRole("tooltip", { hidden: true })).toBeInTheDocument();
    });

    it("tooltip has pointer-events-none so it cannot steal hover", () => {
      render(<HelpTooltip term="polarization" />);
      expect(screen.getByRole("tooltip", { hidden: true })).toHaveClass("pointer-events-none");
    });
  });
});
