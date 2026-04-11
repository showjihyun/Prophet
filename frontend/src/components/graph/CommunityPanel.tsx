/**
 * CommunityPanel — Left sidebar (Zone 2 Left).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-left-community-panel
 *
 * Shows search input, community list with color dots, agent counts,
 * sentiment bars, and total agent count.
 *
 * Data sources — two layered sources, same pattern as GraphPanel:
 *
 *   1. `useCommunities(simulationId)` — the stable list from
 *      `GET /api/v1/simulations/{id}/communities/`. Provides the real
 *      human names ("mainstream", "skeptics"…), UUID ids, and baseline
 *      agent counts. Fetched once per simulation, cached by TanStack.
 *
 *   2. `latestStep.community_metrics` — the live per-step metrics that
 *      arrive via WebSocket and drive the sentiment bar. Keyed by the
 *      same UUID the communities list returns, so we join on
 *      `community_id`. When a step hasn't arrived yet the sentiment
 *      bar is neutral but the list still renders real names.
 *
 * Before this fix the panel read `latestStep.community_metrics` alone
 * and tried to synthesize a display name by uppercasing the first
 * character of the key — which is a UUID. Every community ended up
 * labelled "6 Community" / "0 Community" / "1 Community" and colored
 * identically from a hardcoded `alpha/beta/gamma/delta/bridge` map
 * that no real simulation matches.
 */
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { useCommunities } from "../../api/queries";
import { SkeletonList } from "../shared/LoadingSpinner";
import { SIM_STATUS } from "@/config/constants";
import HelpTooltip from "../shared/HelpTooltip";

interface CommunityItem {
  id: string;
  name: string;
  color: string;
  agents: number;
  sentiment: { positive: number; neutral: number; negative: number };
  /** True when this row is rendered before any real step data has arrived. */
  isPlaceholder?: boolean;
}

/**
 * Stable palette-slot assignment for communities. Mirrors
 * `fallbackColorFor` in GraphPanel.tsx so the left sidebar and the 3D
 * graph pick the same color for the same community. Hashes the id so
 * the assignment is stable across refetches.
 */
const FALLBACK_COMMUNITY_PALETTE: readonly string[] = [
  "#3b82f6", // blue
  "#22c55e", // green
  "#f97316", // orange
  "#a855f7", // purple
  "#ef4444", // red
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
  "#eab308", // yellow
  "#14b8a6", // teal
];

function colorForCommunity(id: string): string {
  let h = 0;
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) | 0;
  }
  return FALLBACK_COMMUNITY_PALETTE[
    Math.abs(h) % FALLBACK_COMMUNITY_PALETTE.length
  ];
}

export default function CommunityPanel() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const highlightedCommunity = useSimulationStore(
    (s) => s.highlightedCommunity,
  );
  const simulationId =
    useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const status = useSimulationStore((s) => s.status);
  const latestStep = useSimulationStore((s) => s.latestStep);

  // TanStack Query — canonical community list from the backend. Contains
  // the real human names, UUIDs, and baseline sizes. Cached per sim id.
  const communitiesQuery = useCommunities(simulationId);

  const communities = useMemo<CommunityItem[]>(() => {
    const list = communitiesQuery.data?.communities ?? [];
    if (list.length === 0) return [];

    // Per-step metrics are keyed by community UUID. Build a lookup once.
    const metricsByUuid: Record<string, { mean_belief?: number; adoption_count?: number; adoption_rate?: number }> = {};
    const raw = latestStep?.community_metrics ?? {};
    for (const [key, value] of Object.entries(raw)) {
      // Backend sends the UUID in both the map key and the inner
      // ``community_id`` field. We prefer the inner field when present
      // because it's the canonical ID the communities endpoint returns.
      const uuid = value?.community_id ?? key;
      metricsByUuid[uuid] = value;
    }

    return list.map((c) => {
      const metrics = metricsByUuid[c.community_id];
      const belief = metrics?.mean_belief ?? c.mean_belief ?? 0;
      const positive = Math.round(Math.max(0, belief) * 100);
      const negative = Math.round(Math.max(0, -belief) * 100);
      const neutral = Math.max(0, 100 - positive - negative);
      // Prefer per-step adoption_count when the step has landed, fall
      // back to the snapshot size from /communities so the row never
      // shows a bogus zero while waiting for the first step.
      const agents =
        metrics?.adoption_count ??
        (metrics?.adoption_rate !== undefined
          ? Math.round(metrics.adoption_rate * c.size)
          : c.size);
      return {
        id: c.community_id,
        name: c.name || c.community_id.slice(0, 8),
        color: colorForCommunity(c.community_id),
        agents,
        sentiment: { positive, neutral, negative },
        isPlaceholder: metrics === undefined,
      };
    });
  }, [communitiesQuery.data, latestStep]);

  const isLoading =
    simulationId !== null &&
    status === SIM_STATUS.RUNNING &&
    communitiesQuery.isLoading &&
    communities.length === 0;

  const filtered = communities.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()),
  );

  const totalAgents = communities.reduce((sum, c) => sum + (c.agents ?? 0), 0);

  return (
    <div
      data-testid="community-panel"
      className="shrink-0 flex flex-col border-r border-[var(--border)] bg-[var(--card)]"
      style={{ width: "var(--community-panel-width)" }}
    >
      {/* Search */}
      <div className="p-3 border-b border-[var(--border)]">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--muted-foreground)]" />
          <input
            type="text"
            placeholder="Filter communities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
          />
        </div>
      </div>

      {/* Title */}
      <div className="flex items-center justify-between px-4 py-2">
        <span className="text-sm font-semibold text-[var(--foreground)] flex items-center gap-1.5">
          Communities
          <HelpTooltip term="community" align="left" />
        </span>
        <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
          {communities.length}
        </span>
      </div>

      {/* Community List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && <SkeletonList rows={5} />}
        {!isLoading && filtered.length === 0 && (
          <div className="px-4 py-6 text-[11px] text-[var(--muted-foreground)] leading-relaxed">
            No matching communities.
          </div>
        )}
        {!isLoading && filtered.map((community) => (
          <CommunityRow
            key={community.id}
            community={community}
            isHighlighted={highlightedCommunity === community.id}
            onClick={() => navigate(`/communities/${community.id}`)}
          />
        ))}
      </div>

      {/* Total */}
      <div className="px-4 py-3 border-t border-[var(--border)]">
        <span className="text-xs font-medium text-[var(--foreground)]">
          Total: {totalAgents.toLocaleString()} Agents
        </span>
      </div>
    </div>
  );
}

function CommunityRow({
  community,
  isHighlighted,
  onClick,
}: {
  community: CommunityItem;
  isHighlighted: boolean;
  onClick: () => void;
}) {
  const isPlaceholder = community.isPlaceholder === true;
  return (
    <div
      onClick={onClick}
      title={isPlaceholder ? "Awaiting first step — values will populate when the simulation runs" : undefined}
      className={`interactive flex items-center gap-3 px-4 cursor-pointer transition-colors hover:bg-[var(--secondary)] ${
        isHighlighted ? "bg-[var(--secondary)]" : ""
      } ${isPlaceholder ? "opacity-50" : ""}`}
      style={{ height: "var(--community-item-height, 48px)" }}
    >
      {/* Color dot */}
      <span
        className="w-2.5 h-2.5 rounded-full shrink-0"
        style={{ backgroundColor: community.color }}
      />

      {/* Name + count */}
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-medium text-[var(--foreground)] truncate">
          {community.name}
        </div>
        <div className="text-[11px] text-[var(--muted-foreground)]">
          {isPlaceholder
            ? "— agents"
            : `${(community.agents ?? 0).toLocaleString()} agents`}
        </div>
      </div>

      {/* Sentiment bar — neutral grey track when placeholder */}
      <div className="w-16 shrink-0">
        <div className="flex h-1.5 rounded-full overflow-hidden bg-[var(--secondary)]">
          {!isPlaceholder && (
            <>
              <div
                className="bg-[var(--sentiment-positive)]"
                style={{ width: `${community.sentiment.positive}%` }}
              />
              <div
                className="bg-[var(--sentiment-neutral)]"
                style={{ width: `${community.sentiment.neutral}%` }}
              />
              <div
                className="bg-[var(--sentiment-negative)]"
                style={{ width: `${community.sentiment.negative}%` }}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
