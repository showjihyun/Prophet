/**
 * Pure helpers + metadata for the EmergentEventsPanel component.
 *
 * Separated from EmergentEventsPanel.tsx so Vite's react-refresh plugin
 * can hot-reload the component in isolation (rule: component files must
 * only export components).
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#emergent-events-panel
 */
import {
  AlertTriangle,
  Flame,
  Network,
  TrendingDown,
  Clock,
  Sparkles,
} from "lucide-react";
import type { EmergentEvent } from "@/types/simulation";

export type EventType = EmergentEvent["event_type"];
export type FilterValue = EventType | "all";

export interface EventTypeMeta {
  label: string;
  icon: typeof Flame;
  color: string;
  description: string;
}

export const EVENT_TYPE_META: Record<EventType, EventTypeMeta> = {
  viral_cascade: {
    label: "Viral Cascade",
    icon: Flame,
    color: "text-orange-400",
    description: "Message spreading rapidly through the network",
  },
  polarization: {
    label: "Polarization",
    icon: Network,
    color: "text-purple-400",
    description: "Population splitting into opposing belief clusters",
  },
  echo_chamber: {
    label: "Echo Chamber",
    icon: Sparkles,
    color: "text-blue-400",
    description: "Community reinforcing its own viewpoint",
  },
  collapse: {
    label: "Collapse",
    icon: TrendingDown,
    color: "text-red-400",
    description: "Adoption rate dropping sharply",
  },
  slow_adoption: {
    label: "Slow Adoption",
    icon: Clock,
    color: "text-amber-400",
    description: "Expected diffusion not materializing",
  },
};

/** Unknown-event fallback. Exported so the panel stays pure-display. */
export const UNKNOWN_EVENT_META: EventTypeMeta = {
  label: "Unknown",
  icon: AlertTriangle,
  color: "text-slate-400",
  description: "Unknown event type",
};

/** Order used for the filter toolbar and stable list sort fallback. */
export const EVENT_TYPE_ORDER: EventType[] = [
  "viral_cascade",
  "polarization",
  "echo_chamber",
  "collapse",
  "slow_adoption",
];

/**
 * Clamp severity to [0, 1] and render as a width percentage. Events coming
 * from the engine should already be in range but we guard against upstream
 * drift so the UI never renders a 250% wide bar.
 */
export function severityToWidth(severity: number): string {
  const clamped = Math.max(0, Math.min(1, severity));
  return `${Math.round(clamped * 100)}%`;
}

/**
 * Apply a type filter to the event list. Returned array is sorted by
 * descending step (most recent first), then by event type for stability.
 */
export function filterAndSortEvents(
  events: EmergentEvent[],
  filter: FilterValue,
): EmergentEvent[] {
  const filtered =
    filter === "all" ? events : events.filter((e) => e.event_type === filter);
  return [...filtered].sort((a, b) => {
    if (b.step !== a.step) return b.step - a.step;
    return (
      EVENT_TYPE_ORDER.indexOf(a.event_type) -
      EVENT_TYPE_ORDER.indexOf(b.event_type)
    );
  });
}
