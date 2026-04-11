/**
 * CommunityPanel — Left sidebar (Zone 2 Left).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-left-community-panel
 *
 * Shows search input, community list with color dots, agent counts,
 * sentiment bars, and total agent count.
 */
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
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

const COMMUNITY_COLOR_MAP: Record<string, string> = {
  alpha: "var(--community-alpha)",
  beta: "var(--community-beta)",
  gamma: "var(--community-gamma)",
  delta: "var(--community-delta)",
  bridge: "var(--community-bridge)",
};

// PLACEHOLDER_COMMUNITIES — shown ONLY when no real community_metrics
// have arrived yet. Lets the user see the palette + the panel structure
// before stepping the simulation. As soon as `latestStep.community_metrics`
// becomes available, real values replace these. Each row carries
// `isPlaceholder: true` so the UI can dim them.
const PLACEHOLDER_COMMUNITIES: CommunityItem[] = [
  {
    id: "alpha",
    name: "Alpha",
    color: "var(--community-alpha)",
    agents: 0,
    sentiment: { positive: 0, neutral: 0, negative: 0 },
    isPlaceholder: true,
  },
  {
    id: "beta",
    name: "Beta",
    color: "var(--community-beta)",
    agents: 0,
    sentiment: { positive: 0, neutral: 0, negative: 0 },
    isPlaceholder: true,
  },
  {
    id: "gamma",
    name: "Gamma",
    color: "var(--community-gamma)",
    agents: 0,
    sentiment: { positive: 0, neutral: 0, negative: 0 },
    isPlaceholder: true,
  },
  {
    id: "delta",
    name: "Delta",
    color: "var(--community-delta)",
    agents: 0,
    sentiment: { positive: 0, neutral: 0, negative: 0 },
    isPlaceholder: true,
  },
  {
    id: "bridge",
    name: "Bridge",
    color: "var(--community-bridge)",
    agents: 0,
    sentiment: { positive: 0, neutral: 0, negative: 0 },
    isPlaceholder: true,
  },
];

export default function CommunityPanel() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const highlightedCommunity = useSimulationStore(
    (s) => s.highlightedCommunity,
  );
  // Subscribe to boolean derived from simulation to avoid re-render on sim object change
  const hasSimulation = useSimulationStore((s) => s.simulation !== null);
  const status = useSimulationStore((s) => s.status);
  const latestStep = useSimulationStore((s) => s.latestStep);
  const hasSteps = useSimulationStore((s) => s.steps.length > 0);
  const isLoading = hasSimulation && status === SIM_STATUS.RUNNING && !hasSteps;

  // Build communities from live data, or fall back to PLACEHOLDER_COMMUNITIES
  // when no step has arrived yet. Placeholders show the palette + structure
  // so the panel never feels empty; they're visually dimmed and replaced as
  // soon as real metrics arrive.
  const communities = useMemo<CommunityItem[]>(() => {
    if (!latestStep?.community_metrics) return PLACEHOLDER_COMMUNITIES;

    return Object.entries(latestStep.community_metrics).map(([id, metrics]) => {
      const belief = metrics.mean_belief ?? 0;
      const positive = Math.round(Math.max(0, belief) * 100);
      const negative = Math.round(Math.max(0, -belief) * 100);
      const neutral = Math.max(0, 100 - positive - negative);
      // adoption_count may not exist in API response; derive from adoption_rate
      const agentCount = metrics.adoption_count
        ?? Math.round((metrics.adoption_rate ?? 0) * 1000);
      return {
        id: metrics.community_id ?? id,
        name: `${id.charAt(0).toUpperCase()}${id.slice(1)} Community`,
        color: COMMUNITY_COLOR_MAP[id.toLowerCase()] ?? "var(--community-alpha)",
        agents: agentCount,
        sentiment: { positive, neutral, negative },
      };
    });
  }, [latestStep]);

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
