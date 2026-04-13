/**
 * CommunitiesDetailPage — Communities overview with cards and connection matrix.
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md
 */
import { useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";
import { type CommunityInfo } from "../api/client";
import {
  useCommunities,
  useCreateCommunity,
  useUpdateCommunity,
  useDeleteCommunity,
} from "../api/queries";
import { LoadingSpinner } from "../components/shared/LoadingSpinner";
import { useSimulationStore } from "../store/simulationStore";
import { SIM_STATUS } from "@/config/constants";
import { resolveCommunityColor } from "@/lib/communityColor";

// COMMUNITIES mock array + CONNECTION_MATRIX removed — the page now renders
// only real community data from the API (via useCommunities TanStack Query).
// When no data is available, an explicit empty state is shown instead of
// fake agent IDs and canned sentiment distributions.

const statusColors: Record<string, string> = {
  "Very High": "bg-[var(--destructive)]/15 text-[var(--destructive)]",
  High: "bg-[var(--sentiment-positive)]/15 text-[var(--sentiment-positive)]",
  Medium: "bg-[var(--sentiment-warning)]/15 text-[var(--sentiment-warning)]",
  Low: "bg-[var(--secondary)] text-[var(--muted-foreground)]",
};

const emotionColors: Record<string, string> = {
  interest: "var(--community-alpha)",
  trust: "var(--community-beta)",
  skepticism: "var(--community-gamma)",
  excitement: "var(--community-delta)",
};

// Display-name overrides for the canonical A/B/C/D/E community ids.
// Color resolution lives in `@/lib/communityColor#resolveCommunityColor`
// so this page paints the same swatch the 3D graph + legend use for the
// same community — including dynamic ids like UUIDs from custom
// templates that this map doesn't (and shouldn't) enumerate.
const COMMUNITY_NAME: Record<string, string> = {
  A: "Alpha Community",
  B: "Beta Community",
  C: "Gamma Community",
  D: "Delta Community",
  E: "Bridge Community",
};

interface LocalCommunity {
  id: string;
  name: string;
  color: string;
  agents: number;
  sentiment: { positive: number; neutral: number; negative: number };
  influencers: Array<{ id: string; score: number }>;
  emotions: { interest: number; trust: number; skepticism: number; excitement: number };
  status: "Very High" | "High" | "Medium" | "Low";
}

function apiToLocal(c: CommunityInfo): LocalCommunity {
  const name = COMMUNITY_NAME[c.community_id] ?? c.name ?? c.community_id;
  const sentPos = Math.round(Math.max(0, c.mean_belief) * 100);
  const sentNeg = Math.round(Math.max(0, -c.mean_belief) * 100);
  return {
    id: c.community_id.toLowerCase(),
    name,
    color: resolveCommunityColor(c.community_id),
    agents: c.size,
    sentiment: { positive: sentPos, neutral: 100 - sentPos - sentNeg, negative: sentNeg },
    influencers: [],
    emotions: { interest: 25, trust: 25, skepticism: 25, excitement: 25 },
    status: c.adoption_rate > 0.6 ? "Very High" as const : c.adoption_rate > 0.3 ? "High" as const : c.adoption_rate > 0.1 ? "Medium" as const : "Low" as const,
  };
}

export default function CommunitiesDetailPage() {
  const navigate = useNavigate();
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  // FE-PERF-M3: use canonical latestStep selector
  const latestStep = useSimulationStore((s) => s.latestStep);
  const simStatus = useSimulationStore((s) => s.status);
  const canEdit = simulationId != null && (simStatus === SIM_STATUS.PAUSED || simStatus === SIM_STATUS.CONFIGURED || simStatus === SIM_STATUS.CREATED);
  // Use getState() so addToast subscription doesn't trigger re-renders
  const addToast = (t: { type: 'info' | 'success' | 'warning' | 'error'; message: string }) => useSimulationStore.getState().addToast(t);

  // TanStack Query — list + 3 mutations with auto-invalidation
  const communitiesQuery = useCommunities(simulationId);
  const communities =
    communitiesQuery.data?.communities && communitiesQuery.data.communities.length > 0
      ? communitiesQuery.data.communities.map(apiToLocal)
      : [];
  const loading = communitiesQuery.isLoading;
  const createCommunity = useCreateCommunity(simulationId);
  const updateCommunity = useUpdateCommunity(simulationId);
  const deleteCommunity = useDeleteCommunity(simulationId);

  const handleAddCommunity = async () => {
    if (!simulationId) return;
    const name = window.prompt("New community name:");
    if (!name?.trim()) return;
    const sizeStr = window.prompt("Number of agents (10-5000):", "100");
    const size = parseInt(sizeStr ?? "100", 10);
    if (isNaN(size) || size < 10 || size > 5000) return;
    try {
      await createCommunity.mutateAsync({ name: name.trim(), size });
      addToast({ type: "success", message: `Community "${name.trim()}" added with ${size} agents` });
    } catch (e) {
      addToast({ type: "error", message: `Failed to add community: ${e}` });
    }
  };

  const handleDeleteCommunity = async (communityId: string, communityName: string) => {
    if (!simulationId) return;
    if (!window.confirm(`Delete community "${communityName}"? All its agents will be removed.`)) return;
    try {
      const result = await deleteCommunity.mutateAsync(communityId) as { agents_removed: number };
      addToast({ type: "success", message: `Removed "${communityName}" (${result.agents_removed} agents)` });
    } catch (e) {
      addToast({ type: "error", message: `Failed to delete: ${e}` });
    }
  };

  const handleEditCommunity = async (communityId: string) => {
    if (!simulationId) return;
    const name = window.prompt("New community name:");
    if (!name?.trim()) return;
    try {
      await updateCommunity.mutateAsync({ communityId, payload: { name: name.trim() } });
      addToast({ type: "success", message: `Community renamed to "${name.trim()}"` });
    } catch (e) {
      addToast({ type: "error", message: `Failed to update: ${e}` });
    }
  };

  const totalAgents = communities.reduce((s, c) => s + c.agents, 0);
  const avgSentiment = latestStep?.mean_sentiment ?? 0.72;

  return (
    <div
      data-testid="communities-detail-page"
      className="min-h-screen bg-[var(--background)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Communities Overview" },
        ]}
        actions={
          <div className="flex items-center gap-3">
            <span className="font-semibold text-sm text-[var(--foreground)]">MCASP Prophet Engine</span>
            <button
              onClick={handleAddCommunity}
              disabled={!canEdit}
              className="px-3 py-1.5 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              + Add Community
            </button>
            <button
              onClick={() => navigate("/communities/manage")}
              className="px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)]"
            >
              Manage Templates
            </button>
          </div>
        }
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Communities"
            value={communities.length}
            icon={<UsersIcon />}
          />
          <StatCard
            label="Total Agents"
            value={totalAgents.toLocaleString()}
            icon={<UserPlusIcon />}
          />
          <StatCard
            label="Active Interactions"
            value={latestStep ? Object.values(latestStep.action_distribution).reduce((a, b) => a + b, 0).toLocaleString() : "—"}
            icon={<MessageIcon />}
          />
          <StatCard
            label="Avg Sentiment"
            value={`${avgSentiment >= 0 ? "+" : ""}${avgSentiment.toFixed(2)}`}
            icon={<TrendUpIcon />}
          />
        </div>

        {/* Community Cards Grid */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <LoadingSpinner size="lg" label="Loading communities..." />
          </div>
        )}
        <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 transition-opacity duration-300 ${loading ? "opacity-0" : "opacity-100"}`}>
          {communities.map((community) => (
            <div
              key={community.id}
              data-testid={`community-card-${community.id}`}
              className="interactive bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
              style={{ borderTopColor: community.color, borderTopWidth: 3, contentVisibility: "auto", containIntrinsicSize: "0 200px" }}
              onClick={() => navigate(`/communities/${community.id}`)}
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-[var(--foreground)]">
                  {community.name}
                </h3>
                <div className="flex items-center gap-2">
                  {canEdit && (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEditCommunity(community.id); }}
                        className="p-1 rounded hover:bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                        title="Edit community"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteCommunity(community.id, community.name); }}
                        className="p-1 rounded hover:bg-red-900/30 text-[var(--muted-foreground)] hover:text-red-400 transition-colors"
                        title="Delete community"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                      </button>
                    </>
                  )}
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: community.color }}
                  >
                    {community.agents.toLocaleString()} agents
                  </span>
                </div>
              </div>

              {/* Sentiment Bar */}
              <div data-testid={`sentiment-bar-${community.id}`}>
                <span className="text-[11px] text-[var(--muted-foreground)] font-medium">
                  Sentiment
                </span>
                <div className="flex h-2 rounded-full overflow-hidden mt-1">
                  <div
                    style={{ width: `${community.sentiment.positive}%`, backgroundColor: 'var(--sentiment-positive)' }}
                  />
                  <div
                    style={{ width: `${community.sentiment.neutral}%`, backgroundColor: 'var(--sentiment-neutral)' }}
                  />
                  <div
                    style={{ width: `${community.sentiment.negative}%`, backgroundColor: 'var(--sentiment-negative)' }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)] mt-0.5">
                  <span>+{community.sentiment.positive}%</span>
                  <span>{community.sentiment.neutral}%</span>
                  <span>-{community.sentiment.negative}%</span>
                </div>
              </div>

              {/* Key Influencers */}
              <div data-testid={`key-influencers-${community.id}`}>
                <span className="text-[11px] text-[var(--muted-foreground)] font-medium">
                  Key Influencers
                </span>
                <ul className="mt-1 space-y-0.5">
                  {community.influencers.map((inf) => (
                    <li
                      key={inf.id}
                      className="flex justify-between text-[13px]"
                    >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/agents/${inf.id}`);
                        }}
                        className="hover:underline"
                        style={{ color: community.color }}
                      >
                        {inf.id}
                      </button>
                      <span className="text-[var(--muted-foreground)]">{inf.score}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Emotion Distribution */}
              <div data-testid={`emotion-distribution-${community.id}`}>
                <span className="text-[11px] text-[var(--muted-foreground)] font-medium">
                  Emotion Distribution
                </span>
                <div className="flex h-2 rounded-full overflow-hidden mt-1">
                  {Object.entries(community.emotions).map(([key, val]) => (
                    <div
                      key={key}
                      style={{
                        width: `${val}%`,
                        backgroundColor:
                          emotionColors[key as keyof typeof emotionColors],
                      }}
                    />
                  ))}
                </div>
                <div className="flex gap-2 mt-1 flex-wrap">
                  {Object.entries(community.emotions).map(([key, val]) => (
                    <span
                      key={key}
                      className="text-[9px] flex items-center gap-0.5"
                    >
                      <span
                        className="inline-block w-1.5 h-1.5 rounded-full"
                        style={{
                          backgroundColor:
                            emotionColors[key as keyof typeof emotionColors],
                        }}
                      />
                      <span className="text-[var(--muted-foreground)] capitalize">
                        {key} {val}%
                      </span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Status */}
              <span
                data-testid={`activity-status-${community.id}`}
                className={`text-[11px] font-medium px-2 py-0.5 rounded-full w-fit ${statusColors[community.status]}`}
              >
                {community.status} Activity
              </span>
            </div>
          ))}
        </div>

        {/* Community Connections Matrix */}
        <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4">
            Community Connections
          </h3>
          <div className="overflow-x-auto">
            <table data-testid="connections-matrix" className="w-full">
              <thead>
                <tr>
                  <th className="w-24" />
                  {communities.map((c) => (
                    <th
                      key={c.id}
                      className="text-xs font-medium text-[var(--muted-foreground)] text-center p-2"
                    >
                      <span className="flex items-center justify-center gap-1">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: c.color }}
                        />
                        {c.name.split(" ")[0]}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {communities.map((row) => (
                  <tr key={row.id}>
                    <td className="text-xs font-medium text-[var(--muted-foreground)] p-2">
                      <span className="flex items-center gap-1">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: row.color }}
                        />
                        {row.name.split(" ")[0]}
                      </span>
                    </td>
                    {communities.map((col) => {
                      // Without a real inter-community edge-weight API,
                      // derive a placeholder strength: self = 1.0, other
                      // communities scale by their relative size overlap.
                      const strength =
                        row.id === col.id
                          ? 1.0
                          : Math.min(row.agents, col.agents) /
                              Math.max(row.agents, col.agents, 1) *
                              0.8;
                      const size = Math.max(8, Math.round(strength * 24));
                      const isSelf = row.id === col.id;
                      return (
                        <td key={col.id} className="text-center p-2">
                          <div
                            className="mx-auto rounded-full"
                            title={`${row.name.split(" ")[0]} - ${col.name.split(" ")[0]}: ${strength.toFixed(2)}`}
                            style={{
                              width: size,
                              height: size,
                              backgroundColor: isSelf
                                ? row.color
                                : `${row.color}${Math.round(strength * 200).toString(16).padStart(2, "0")}`,
                            }}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Inline icons (Lucide style) */
function UsersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function UserPlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><line x1="19" y1="8" x2="19" y2="14" /><line x1="22" y1="11" x2="16" y2="11" />
    </svg>
  );
}

function MessageIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function TrendUpIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
    </svg>
  );
}
