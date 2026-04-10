/**
 * InjectEventModal — Tests for event injection modal.
 * @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
 * @spec docs/spec/07_FRONTEND_SPEC.md#control-panel
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useSimulationStore } from "../store/simulationStore";

const mockMutateAsync = vi.fn();
const mockInjectEvent = {
  mutateAsync: mockMutateAsync,
  isPending: false,
};

vi.mock("@/api/queries", () => ({
  useInjectEvent: () => mockInjectEvent,
}));

import InjectEventModal from "@/components/shared/InjectEventModal";

const MOCK_SIMULATION = {
  simulation_id: "sim-inject-001",
  project_id: "proj-001",
  scenario_id: "scen-001",
  name: "Inject Event Test",
  status: "running" as const,
  current_step: 10,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

describe("InjectEventModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSimulationStore.setState({ simulation: MOCK_SIMULATION });
    mockMutateAsync.mockResolvedValue({
      event_id: "evt-12345678-abcd",
      effective_step: 11,
    });
    mockInjectEvent.isPending = false;
  });

  it("does not render when isOpen is false", () => {
    render(<InjectEventModal isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders modal with form when isOpen is true", () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // "Inject Event" appears in header (h2) and submit button — check heading
    expect(screen.getByRole("heading", { name: /inject event/i })).toBeInTheDocument();
    expect(screen.getByText("Event Type")).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeInTheDocument();
    expect(screen.getByText("Controversy Level")).toBeInTheDocument();
  });

  it("renders all 6 event type options", () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    const options = select.querySelectorAll("option");
    expect(options.length).toBe(6);
  });

  it("renders community toggle buttons A-E", () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    ["A", "B", "C", "D", "E"].forEach((c) => {
      expect(screen.getByRole("button", { name: c })).toBeInTheDocument();
    });
  });

  it("toggles community selection on click", () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    const btnA = screen.getByRole("button", { name: "A" });
    fireEvent.click(btnA);
    // After click, button should have primary styling (bg-[var(--primary)])
    expect(btnA.className).toContain("bg-[var(--primary)]");
    // Click again to deselect
    fireEvent.click(btnA);
    expect(btnA.className).not.toContain("bg-[var(--primary)] text-[var(--primary-foreground)]");
  });

  it("shows error when content is empty and submit is clicked", async () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    // The submit button contains icon + text "Inject Event"
    const buttons = screen.getAllByRole("button");
    const submitBtn = buttons.find((b) => b.textContent?.includes("Inject Event"));
    expect(submitBtn).toBeTruthy();
    fireEvent.click(submitBtn!);
    await waitFor(() => {
      expect(screen.getByText("Content is required")).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("calls mutateAsync with correct payload on submit", async () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);

    // Fill content
    const textarea = screen.getByPlaceholderText(/describe the event/i);
    fireEvent.change(textarea, { target: { value: "Battery explosion reported" } });

    // Submit
    const submitBtn = screen.getAllByRole("button").find((b) => b.textContent?.includes("Inject Event"))!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        simId: "sim-inject-001",
        event: {
          event_type: "controversy",
          content: "Battery explosion reported",
          controversy: 0.5,
          target_communities: undefined,
        },
      });
    });
  });

  it("sends selected communities in payload", async () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);

    // Fill content
    const textarea = screen.getByPlaceholderText(/describe the event/i);
    fireEvent.change(textarea, { target: { value: "Test event" } });

    // Select communities A and C
    fireEvent.click(screen.getByRole("button", { name: "A" }));
    fireEvent.click(screen.getByRole("button", { name: "C" }));

    const submitBtn = screen.getAllByRole("button").find((b) => b.textContent?.includes("Inject Event"))!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        simId: "sim-inject-001",
        event: expect.objectContaining({
          target_communities: ["A", "C"],
        }),
      });
    });
  });

  it("shows success view after successful injection", async () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/describe the event/i);
    fireEvent.change(textarea, { target: { value: "Test" } });

    const submitBtn = screen.getAllByRole("button").find((b) => b.textContent?.includes("Inject Event"))!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Event Injected")).toBeInTheDocument();
    });
    expect(screen.getByText("evt-1234")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
  });

  it("shows error message on mutation failure", async () => {
    mockMutateAsync.mockRejectedValueOnce(new Error("Server error"));
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/describe the event/i);
    fireEvent.change(textarea, { target: { value: "Test" } });

    const submitBtn = screen.getAllByRole("button").find((b) => b.textContent?.includes("Inject Event"))!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    render(<InjectEventModal isOpen={true} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<InjectEventModal isOpen={true} onClose={onClose} />);
    // The backdrop is the first child div with bg-black/50
    const backdrop = document.querySelector(".bg-black\\/50");
    expect(backdrop).toBeTruthy();
    fireEvent.click(backdrop!);
    expect(onClose).toHaveBeenCalled();
  });

  it("changes event type via select", async () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "news_article" } });

    const textarea = screen.getByPlaceholderText(/describe the event/i);
    fireEvent.change(textarea, { target: { value: "News" } });

    const submitBtn = screen.getAllByRole("button").find((b) => b.textContent?.includes("Inject Event"))!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          event: expect.objectContaining({ event_type: "news_article" }),
        }),
      );
    });
  });

  it("adjusts controversy slider", () => {
    render(<InjectEventModal isOpen={true} onClose={vi.fn()} />);
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "0.8" } });
    expect(screen.getByText("0.80")).toBeInTheDocument();
  });
});
