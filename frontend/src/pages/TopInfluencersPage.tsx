/**
 * TopInfluencersPage — Ranked influencer table with distribution sidebar.
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 * @spec docs/spec/ui/UI_08_INFLUENCERS_PAGINATION.md
 * @spec docs/spec/ui/UI_09_INFLUENCERS_FILTER.md
 */
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { type AgentSummary } from "../api/client";
import { useAgents, useNetwork } from "../api/queries";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { useSimulationStore } from "../store/simulationStore";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";
import InfluencersFilter from "../components/shared/InfluencersFilter";
import {
  DEFAULT_FILTERS,
  type FilterState,
} from "../components/shared/influencersFilterTypes";

interface Influencer {
  rank: number;
  agentId: string;
  community: string;
  communityColor: string;
  influenceScore: number;
  sentiment: "Positive" | "Neutral" | "Negative";
  chains: number;
  connections: number;
  status: "Active" | "Idle";
}

/* ---------- expanded mock data (30 records for pagination demo) ---------- */

const COMMUNITY_COLORS: Record<string, string> = {
  Alpha: "var(--community-alpha)",
  Beta: "var(--community-beta)",
  Gamma: "var(--community-gamma)",
  Delta: "var(--community-delta)",
  Bridge: "var(--community-bridge)",
};

// MOCK_INFLUENCERS / DISTRIBUTION_DATA removed — page now requires a real
// simulation and shows an empty state otherwise (see render below).

const SENTIMENT_STYLES: Record<string, React.CSSProperties> = {
  Positive: { backgroundColor: "color-mix(in srgb, var(--sentiment-positive) 15%, transparent)", color: "var(--sentiment-positive)" },
  Neutral: { backgroundColor: "color-mix(in srgb, var(--sentiment-neutral) 15%, transparent)", color: "var(--sentiment-neutral)" },
  Negative: { backgroundColor: "color-mix(in srgb, var(--sentiment-negative) 15%, transparent)", color: "var(--sentiment-negative)" },
};

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  Active: { backgroundColor: "color-mix(in srgb, var(--sentiment-positive) 15%, transparent)", color: "var(--sentiment-positive)" },
  Idle: { backgroundColor: "var(--secondary)", color: "var(--muted-foreground)" },
};

const COMMUNITY_ID_TO_NAME: Record<string, string> = {
  A: "Alpha", B: "Beta", C: "Gamma", D: "Delta", E: "Bridge",
};

function agentToInfluencer(
  a: AgentSummary,
  rank: number,
  connections: number,
  chains: number,
): Influencer {
  const community = COMMUNITY_ID_TO_NAME[a.community_id] ?? a.community_id;
  return {
    rank,
    agentId: a.agent_id,
    community,
    communityColor: COMMUNITY_COLORS[community] ?? "var(--muted-foreground)",
    influenceScore: Math.round(a.influence_score * 1000) / 10,
    sentiment: a.belief > 0.1 ? "Positive" : a.belief < -0.1 ? "Negative" : "Neutral",
    chains,
    connections,
    status: a.action !== "idle" ? "Active" : "Idle",
  };
}

export default function TopInfluencersPage() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const simulationId = simulation?.simulation_id ?? null;
  const [search, setSearch] = useState("");
  // TanStack Query — cached agents list and network graph, instant on revisit
  const agentsQuery = useAgents(simulationId, { limit: 200 });
  const networkQuery = useNetwork(simulationId);
  const loading = agentsQuery.isLoading;

  // Derive influencers + distribution + stats from query data in a single memo
  const { influencers, distributionData, stats } = useMemo(() => {
    if (!agentsQuery.data) {
      return {
        influencers: [] as Influencer[],
        distributionData: [] as { name: string; value: number; fill: string }[],
        stats: { total: 0, avg: 0, active: 0, bridges: 0 },
      };
    }
    const items: AgentSummary[] = agentsQuery.data.items;

    // Build degree map from network graph (total edges per agent)
    // and incoming-edge map (agents that point TO each agent = chains proxy)
    const degreeMap = new Map<string, number>();
    const incomingMap = new Map<string, number>();
    if (networkQuery.data) {
      for (const edge of networkQuery.data.edges) {
        const src = String(edge.data.source);
        const tgt = String(edge.data.target);
        degreeMap.set(src, (degreeMap.get(src) ?? 0) + 1);
        degreeMap.set(tgt, (degreeMap.get(tgt) ?? 0) + 1);
        incomingMap.set(tgt, (incomingMap.get(tgt) ?? 0) + 1);
      }
    }

    const sorted = [...items].sort((a, b) => b.influence_score - a.influence_score);
    const _influencers = sorted.map((a, i) =>
      agentToInfluencer(
        a,
        i + 1,
        degreeMap.get(a.agent_id) ?? 0,
        incomingMap.get(a.agent_id) ?? 0,
      ),
    );

    // Compute distribution
    const commCounts: Record<string, number> = {};
    for (const a of items) {
      const name = COMMUNITY_ID_TO_NAME[a.community_id] ?? a.community_id;
      commCounts[name] = (commCounts[name] ?? 0) + 1;
    }
    const _distributionData = Object.entries(commCounts).map(([name, value]) => ({
      name,
      value,
      fill: COMMUNITY_COLORS[name] ?? "var(--muted-foreground)",
    }));

    // Compute stats in a single pass
    let scoreSum = 0;
    let activeCount = 0;
    let bridgeCount = 0;
    for (const a of items) {
      scoreSum += a.influence_score * 100;
      if (a.action !== "idle") activeCount++;
      if (a.agent_type === "bridge") bridgeCount++;
    }
    const count = items.length;
    return {
      influencers: _influencers,
      distributionData: _distributionData,
      stats: {
        total: agentsQuery.data.total,
        avg: count ? Math.round((scoreSum / count) * 10) / 10 : 0,
        active: activeCount,
        bridges: bridgeCount,
      },
    };
  }, [agentsQuery.data, networkQuery.data]);

  // Sort state (A1)
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'influence_score', direction: 'desc' });

  const handleSort = (key: string) => {
    setSortConfig((prev) =>
      prev.key === key
        ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: 'desc' }
    );
    setCurrentPage(1);
  };

  // Pagination state (UI-08)
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // Filter state (UI-09)
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>({ ...DEFAULT_FILTERS });

  // Apply search + filters + sort
  const filtered = useMemo(() => {
    const result = influencers.filter((i) => {
      // Search
      if (
        search &&
        !i.agentId.toLowerCase().includes(search.toLowerCase()) &&
        !i.community.toLowerCase().includes(search.toLowerCase())
      ) {
        return false;
      }
      // Community filter
      if (!filters.communities.includes(i.community)) return false;
      // Status filter
      if (filters.status !== "all" && i.status.toLowerCase() !== filters.status) return false;
      // Score range
      if (i.influenceScore < filters.scoreMin || i.influenceScore > filters.scoreMax) return false;
      // Sentiment
      if (filters.sentiment !== "all" && i.sentiment !== filters.sentiment) return false;
      // Min connections
      if (i.connections < filters.minConnections) return false;
      return true;
    });

    // Apply sort
    return [...result].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;
      if (sortConfig.key === 'influence_score') {
        aVal = a.influenceScore;
        bVal = b.influenceScore;
      } else if (sortConfig.key === 'community_id') {
        aVal = a.community;
        bVal = b.community;
      } else if (sortConfig.key === 'belief') {
        const sentimentOrder: Record<string, number> = { Positive: 1, Neutral: 0, Negative: -1 };
        aVal = sentimentOrder[a.sentiment] ?? 0;
        bVal = sentimentOrder[b.sentiment] ?? 0;
      } else {
        return 0;
      }
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [search, filters, influencers, sortConfig]);

  // Top Community: community with most agents in the filtered list (A10)
  const topCommunity = useMemo(() => {
    if (filtered.length === 0) return "—";
    const counts: Record<string, number> = {};
    for (const i of filtered) {
      counts[i.community] = (counts[i.community] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";
  }, [filtered]);

  // Pagination derived values
  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / rowsPerPage));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedData = filtered.slice(
    (safePage - 1) * rowsPerPage,
    safePage * rowsPerPage
  );

  // Reset to page 1 on search change
  const handleSearch = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  // Filter apply handler
  const handleApplyFilters = (newFilters: FilterState) => {
    setFilters(newFilters);
    setFilterOpen(false);
    setCurrentPage(1);
  };

  // Count active filters (for badge)
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.communities.length < 5) count++;
    if (filters.status !== "all") count++;
    if (filters.scoreMin > 0 || filters.scoreMax < 100) count++;
    if (filters.sentiment !== "all") count++;
    if (filters.minConnections > 0) count++;
    return count;
  }, [filters]);

  // Page numbers to display (window of up to 5)
  const pageNumbers = useMemo(() => {
    const pages: number[] = [];
    let start = Math.max(1, safePage - 2);
    const end = Math.min(totalPages, start + 4);
    start = Math.max(1, end - 4);
    for (let p = start; p <= end; p++) {
      pages.push(p);
    }
    return pages;
  }, [safePage, totalPages]);

  return (
    <div
      data-testid="top-influencers-page"
      className="min-h-screen bg-[var(--muted)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Top Influencers" },
        ]}
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto">
        {/* Empty state — no simulation selected */}
        {!simulation && !loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <CrownIcon />
            <p className="text-sm text-[var(--muted-foreground)]">
              No active simulation. Run a simulation first to view influencer rankings.
            </p>
            <button
              onClick={() => navigate("/projects")}
              className="mt-2 h-9 px-5 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
            >
              Go to Projects
            </button>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-24">
            <LoadingSpinner label="Loading agents..." />
          </div>
        )}

        {/* Main content — only when simulation is active */}
        {simulation && !loading && (<>
        {/* Summary Stats — updated per UI-08 SPEC */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Influencers Tracked" value={String(stats.total)} icon={<CrownIcon />} term="influencer" />
          <StatCard label="Avg Influence Score" value={String(stats.avg)} icon={<BarChartIcon />} term="influenceScore" />
          <StatCard label="Top Community" value={topCommunity} icon={<UsersIcon />} term="topCommunity" />
          <StatCard label="Active Cascades" value={String(stats.active)} icon={<GitBranchIcon />} term="viralCascade" tooltipAlign="right" />
        </div>

        {/* Content area: table + sidebar */}
        <div className="flex gap-6">
          {/* Main table area */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Search + Filter */}
            <div className="flex gap-3 relative">
              <div className="relative flex-1">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]"
                  width="16"
                  height="16"
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Search agents..."
                  aria-label="Search agents"
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full h-10 pl-9 pr-4 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
              </div>
              <button
                onClick={() => setFilterOpen(true)}
                className="h-10 px-4 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
                Filter
                {activeFilterCount > 0 && (
                  <span
                    className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-medium text-white"
                    style={{ backgroundColor: "var(--primary)" }}
                  >
                    {activeFilterCount}
                  </span>
                )}
              </button>

              {/* Filter Popover (UI-09) */}
              <InfluencersFilter
                isOpen={filterOpen}
                onClose={() => setFilterOpen(false)}
                onApply={handleApplyFilters}
                currentFilters={filters}
              />
            </div>

            {/* Data Table */}
            <div className="table-scroll-wrapper bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm overflow-hidden">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--muted)]">
                    <th className="text-right px-3 py-3 font-semibold text-[var(--muted-foreground)] w-12">#</th>
                    <th className="text-left px-3 py-3 font-semibold text-[var(--muted-foreground)]">Agent ID</th>
                    <th
                      className="text-left px-3 py-3 font-semibold text-[var(--muted-foreground)] cursor-pointer hover:text-[var(--foreground)] select-none"
                      onClick={() => handleSort('community_id')}
                    >
                      <span>Community</span>
                      {sortConfig.key === 'community_id' && (
                        <span className="ml-1 text-xs">{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                      )}
                    </th>
                    <th
                      className="text-left px-3 py-3 font-semibold text-[var(--muted-foreground)] w-48 cursor-pointer hover:text-[var(--foreground)] select-none"
                      onClick={() => handleSort('influence_score')}
                    >
                      <span>Influence Score</span>
                      {sortConfig.key === 'influence_score' && (
                        <span className="ml-1 text-xs">{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                      )}
                    </th>
                    <th
                      className="text-left px-3 py-3 font-semibold text-[var(--muted-foreground)] cursor-pointer hover:text-[var(--foreground)] select-none"
                      onClick={() => handleSort('belief')}
                    >
                      <span>Sentiment</span>
                      {sortConfig.key === 'belief' && (
                        <span className="ml-1 text-xs">{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                      )}
                    </th>
                    <th className="text-right px-3 py-3 font-semibold text-[var(--muted-foreground)]">Chains</th>
                    <th className="text-right px-3 py-3 font-semibold text-[var(--muted-foreground)]">Connections</th>
                    <th className="text-left px-3 py-3 font-semibold text-[var(--muted-foreground)]">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedData.map((inf) => (
                    <tr
                      key={inf.agentId}
                      className="interactive border-b border-[var(--border)] hover:bg-[var(--accent)] transition-colors cursor-pointer"
                      style={{ contentVisibility: "auto", containIntrinsicSize: "0 48px" }}
                      onClick={() => navigate(`/agents/${inf.agentId}`)}
                    >
                      <td className="text-right px-3 py-3 font-semibold text-[var(--muted-foreground)]">
                        {inf.rank}
                      </td>
                      <td className="px-3 py-3 font-medium text-[var(--community-alpha)] hover:underline">
                        {inf.agentId}
                      </td>
                      <td className="px-3 py-3">
                        <span data-testid={`community-badge-${inf.agentId}`} className="inline-flex items-center gap-1.5">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: inf.communityColor }}
                          />
                          {inf.community}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div data-testid={`influence-score-bar-${inf.agentId}`} className="flex-1 h-2 rounded-full bg-[var(--muted)] overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{ width: `${inf.influenceScore}%`, backgroundColor: inf.communityColor }}
                            />
                          </div>
                          <span className="text-xs font-medium w-10 text-right">
                            {inf.influenceScore}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                          style={SENTIMENT_STYLES[inf.sentiment]}
                        >
                          {inf.sentiment}
                        </span>
                      </td>
                      <td className="text-right px-3 py-3">{inf.chains}</td>
                      <td className="text-right px-3 py-3">
                        {inf.connections}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          data-testid={`status-badge-${inf.agentId}`}
                          className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                          style={STATUS_STYLES[inf.status]}
                        >
                          {inf.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination Bar (UI-08) */}
              <div
                data-testid="table-pagination"
                className="flex items-center justify-between border-t px-4 py-3"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                  Showing {total === 0 ? 0 : (safePage - 1) * rowsPerPage + 1}-{Math.min(safePage * rowsPerPage, total)} of {total} influencers
                </span>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
                      Rows per page:
                    </span>
                    <select
                      aria-label="Rows per page"
                      value={rowsPerPage}
                      onChange={(e) => {
                        setRowsPerPage(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className="rounded-md border px-2 py-1 text-sm"
                      style={{ borderColor: "var(--border)" }}
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      aria-label="Previous page"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={safePage === 1}
                      className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                      style={{ borderColor: "var(--border)" }}
                    >
                      Previous
                    </button>
                    {pageNumbers.map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        aria-label={`Page ${page}`}
                        aria-current={page === safePage ? "page" : undefined}
                        className={`rounded-md px-3 py-1 text-sm ${page === safePage ? "font-bold" : ""}`}
                        style={{
                          backgroundColor: page === safePage ? "var(--primary)" : "transparent",
                          color: page === safePage ? "var(--primary-foreground)" : "var(--foreground)",
                        }}
                      >
                        {page}
                      </button>
                    ))}
                    <button
                      aria-label="Next page"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={safePage === totalPages}
                      className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                      style={{ borderColor: "var(--border)" }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="w-[280px] shrink-0">
            <div data-testid="influence-distribution-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-[var(--foreground)]">
                  Influence Distribution
                </h3>
                {filters.communities.length < 5 && (
                  <button
                    onClick={() => {
                      setFilters((prev) => ({ ...prev, communities: ["Alpha", "Beta", "Gamma", "Delta", "Bridge"] }));
                      setCurrentPage(1);
                    }}
                    className="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] underline"
                  >
                    Clear
                  </button>
                )}
              </div>
              <p className="text-[11px] text-[var(--muted-foreground)] mb-3">
                Click a bar to filter by community.
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={distributionData}
                  layout="vertical"
                  margin={{ top: 0, right: 8, bottom: 0, left: 0 }}
                >
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={56}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(value: number, _name: string, props: { payload: { name: string } }) => [
                      `${value} influencers`,
                      props.payload.name,
                    ]}
                  />
                  <Bar
                    dataKey="value"
                    radius={[0, 4, 4, 0]}
                    style={{ cursor: "pointer" }}
                    onClick={(data: { name: string }) => {
                      setFilters((prev) => ({
                        ...prev,
                        communities: [data.name],
                      }));
                      setCurrentPage(1);
                    }}
                  >
                    {distributionData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={entry.fill}
                        opacity={
                          filters.communities.length === 5 || filters.communities.includes(entry.name)
                            ? 1
                            : 0.35
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        </>)}
      </div>
    </div>
  );
}

/* Inline icons */
function CrownIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4l3 12h14l3-12-5 4-5-6-5 6-5-4z" /><path d="M3 20h18" />
    </svg>
  );
}

function BarChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function GitBranchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  );
}
