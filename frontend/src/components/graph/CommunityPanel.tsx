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

interface CommunityItem {
  id: string;
  name: string;
  color: string;
  agents: number;
  sentiment: { positive: number; neutral: number; negative: number };
}

const COMMUNITY_COLOR_MAP: Record<string, string> = {
  alpha: "var(--community-alpha)",
  beta: "var(--community-beta)",
  gamma: "var(--community-gamma)",
  delta: "var(--community-delta)",
  bridge: "var(--community-bridge)",
};

const MOCK_COMMUNITIES: CommunityItem[] = [
  {
    id: "alpha",
    name: "Alpha",
    color: "var(--community-alpha)",
    agents: 1500,
    sentiment: { positive: 62, neutral: 25, negative: 13 },
  },
  {
    id: "beta",
    name: "Beta",
    color: "var(--community-beta)",
    agents: 1200,
    sentiment: { positive: 55, neutral: 30, negative: 15 },
  },
  {
    id: "gamma",
    name: "Gamma",
    color: "var(--community-gamma)",
    agents: 1100,
    sentiment: { positive: 40, neutral: 35, negative: 25 },
  },
  {
    id: "delta",
    name: "Delta",
    color: "var(--community-delta)",
    agents: 1400,
    sentiment: { positive: 48, neutral: 32, negative: 20 },
  },
  {
    id: "bridge",
    name: "Bridge",
    color: "var(--community-bridge)",
    agents: 300,
    sentiment: { positive: 35, neutral: 40, negative: 25 },
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

  // Build communities from live data or fall back to mock
  const communities = useMemo<CommunityItem[]>(() => {
    if (!latestStep?.community_metrics) return MOCK_COMMUNITIES;

    return Object.entries(latestStep.community_metrics).map(([id, metrics]) => {
      const belief = metrics.mean_belief ?? 0;
      const positive = Math.round(Math.max(0, belief) * 100);
      const negative = Math.round(Math.max(0, -belief) * 100);
      const neutral = Math.max(0, 100 - positive - negative);
      // adoption_count may not exist in API response; derive from adoption_rate
      const agentCount = metrics.adoption_count
        ?? (metrics.size != null ? metrics.size : Math.round((metrics.adoption_rate ?? 0) * 1000));
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
        <span className="text-sm font-semibold text-[var(--foreground)]">
          Communities
        </span>
        <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
          {communities.length}
        </span>
      </div>

      {/* Community List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && <SkeletonList rows={5} />}
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
  return (
    <div
      onClick={onClick}
      className={`interactive flex items-center gap-3 px-4 cursor-pointer transition-colors hover:bg-[var(--secondary)] ${
        isHighlighted ? "bg-[var(--secondary)]" : ""
      }`}
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
          {(community.agents ?? 0).toLocaleString()} agents
        </div>
      </div>

      {/* Sentiment bar */}
      <div className="w-16 shrink-0">
        <div className="flex h-1.5 rounded-full overflow-hidden">
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
        </div>
      </div>
    </div>
  );
}
