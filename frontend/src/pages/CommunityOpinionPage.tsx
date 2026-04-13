/**
 * CommunityOpinionPage — Community-level opinion clusters + conversations (Level 2).
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-l2
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import HelpTooltip from "../components/shared/HelpTooltip";
import EliteLLMNarrativePanel from "../components/community/EliteLLMNarrativePanel";
import { useSimulationSteps, useCommunityThreads } from "../api/queries";
import { useSimulationStore } from "../store/simulationStore";
import { sentimentTextClass } from "../utils/sentiment";

/* ------------------------------------------------------------------ */
/* Mock Data                                                           */
/* ------------------------------------------------------------------ */

interface ClusterData {
  cluster_id: string;
  topic_name: string;
  description: string;
  agent_count: number;
  stances: { support: number; neutral: number; oppose: number };
}

interface ConversationData {
  thread_id: string;
  topic_title: string;
  participant_ids: string[];
  message_count: number;
  relative_time: string;
}

// COMMUNITY_META / MOCK_CLUSTERS / MOCK_CONVERSATIONS removed — all
// community data is derived from the real simulation store + API now.
// Colors and display names come from the shared COMMUNITIES config; numeric
// counts come from `latestStep.community_metrics`. Missing data shows an
// explicit empty state instead of a hardcoded Election Reform debate.
const COMMUNITY_COLOR_BY_KEY: Record<string, string> = {
  alpha: "var(--community-alpha)",
  beta: "var(--community-beta)",
  gamma: "var(--community-gamma)",
  delta: "var(--community-delta)",
  bridge: "var(--community-bridge)",
};

/* ------------------------------------------------------------------ */
/* Stance Bar                                                          */
/* ------------------------------------------------------------------ */

function StanceBar({ stances }: { stances: { support: number; neutral: number; oppose: number } }) {
  return (
    <div className="flex h-2 w-full rounded-full overflow-hidden">
      <div className="h-full" style={{ width: `${stances.support}%`, backgroundColor: "var(--sentiment-positive)" }} />
      <div className="h-full" style={{ width: `${stances.neutral}%`, backgroundColor: "var(--sentiment-neutral)" }} />
      <div className="h-full" style={{ width: `${stances.oppose}%`, backgroundColor: "var(--sentiment-negative)" }} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

const COMMUNITY_COLORS_MAP: Record<number, string> = {
  0: "var(--community-alpha)",
  1: "var(--community-beta)",
  2: "var(--community-gamma)",
  3: "var(--community-delta)",
  4: "var(--community-bridge)",
};

type SortMode = "mentioned" | "contested" | "newest";

export default function CommunityOpinionPage() {
  const { communityId } = useParams<{ communityId: string }>();
  const navigate = useNavigate();
  const simulation = useSimulationStore((st) => st.simulation);
  const steps = useSimulationStore((st) => st.steps);
  const [sortMode, setSortMode] = useState<SortMode>("mentioned");
  const simId = simulation?.simulation_id ?? null;

  // TanStack Query — bulk hydrate the store once when the live array is empty
  const stepsQuery = useSimulationSteps(steps.length === 0 ? simId : null);
  useEffect(() => {
    if (stepsQuery.data && steps.length === 0) {
      useSimulationStore.getState().setStepsBulk(stepsQuery.data);
    }
  }, [stepsQuery.data, steps.length]);

  // Real recent-conversation threads from the backend (preferred over the
  // synthetic step-derived list). SPEC 27 §5.2 — opinions-l2-threads.
  const threadsQuery = useCommunityThreads(simId, communityId ?? null);
  const apiThreads = useMemo(
    () => threadsQuery.data?.threads ?? [],
    [threadsQuery.data],
  );

  // Derive community meta from store steps
  const derivedMeta = useMemo(() => {
    if (!communityId || steps.length === 0) return null;
    const latestStep = steps[steps.length - 1];
    const cm = latestStep.community_metrics?.[communityId];
    if (!cm) return null;
    const totalAgents = cm.adoption_count > 0 ? Math.round(cm.adoption_count / Math.max(0.001, cm.adoption_rate)) : 0;
    const communityKeys = Object.keys(latestStep.community_metrics ?? {});
    const colorIdx = communityKeys.indexOf(communityId);
    return {
      name: `Community ${communityId}`,
      color: COMMUNITY_COLORS_MAP[colorIdx >= 0 ? colorIdx % 5 : 0] ?? "var(--muted-foreground)",
      agents: totalAgents,
      sentiment: cm.mean_belief,
      conversations: cm.new_propagation_count,
      positive_pct: Math.round(Math.max(0, cm.mean_belief) * 100),
    };
  }, [communityId, steps]);

  // Build time-series clusters from steps
  const derivedClusters = useMemo<ClusterData[]>(() => {
    if (!communityId || steps.length === 0) return [];
    const recent = steps.slice(-5);
    return recent.map((step) => {
      const cm = step.community_metrics?.[communityId];
      const adoptRate = cm?.adoption_rate ?? 0;
      const support = Math.round(adoptRate * 100);
      const oppose = cm && cm.mean_belief < 0 ? Math.round(-cm.mean_belief * 100) : 0;
      return {
        cluster_id: `step-${step.step}`,
        topic_name: `Step ${step.step} Activity`,
        description: `Dominant action: ${cm?.dominant_action ?? "unknown"}. Propagation events: ${cm?.new_propagation_count ?? 0}.`,
        agent_count: cm ? Math.round(cm.adoption_count / Math.max(0.001, cm.adoption_rate)) : 0,
        stances: { support, neutral: Math.max(0, 100 - support - oppose), oppose },
      } satisfies ClusterData;
    });
  }, [communityId, steps]);

  // Build conversations from action_distribution in steps
  const derivedConversations = useMemo<ConversationData[]>(() => {
    if (steps.length === 0) return [];
    return steps.slice(-4).reverse().map((step, idx) => {
      const cm = communityId ? step.community_metrics?.[communityId] : null;
      return {
        thread_id: `step-thread-${step.step}`,
        topic_title: `Step ${step.step}: ${Object.entries(step.action_distribution ?? {}).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "activity"} dominant (${Math.round(step.adoption_rate * 100)}% adoption)`,
        participant_ids: Object.keys(step.community_metrics ?? {}).slice(0, 4),
        message_count: cm?.new_propagation_count ?? step.llm_calls_this_step,
        relative_time: `${idx + 1} step${idx > 0 ? "s" : ""} ago`,
      };
    });
  }, [steps, communityId]);

  // Real-data-only: derive meta from store, or fall back to a minimal
  // placeholder keyed on the URL communityId (name + color only, counts = 0).
  const meta =
    derivedMeta ?? {
      name: `Community ${(communityId ?? "").charAt(0).toUpperCase()}${(communityId ?? "").slice(1)}`.trim() || "Community",
      color: COMMUNITY_COLOR_BY_KEY[(communityId ?? "").toLowerCase()] ?? "var(--muted-foreground)",
      agents: 0,
      sentiment: 0,
      conversations: 0,
      positive_pct: 0,
    };
  const sortedClusters = useMemo(() => {
    const copy = [...derivedClusters];
    if (sortMode === "contested") copy.sort((a, b) => Math.abs(a.stances.support - a.stances.oppose) - Math.abs(b.stances.support - b.stances.oppose));
    else if (sortMode === "newest") copy.reverse();
    else copy.sort((a, b) => b.agent_count - a.agent_count);
    return copy;
  }, [derivedClusters, sortMode]);
  const clusters = sortedClusters;

  // SPEC 27 §5.2 — prefer real API threads; fall back to step-derived only
  // when the API list is empty (older sims with no persisted threads).
  const conversations: ConversationData[] = useMemo(() => {
    if (apiThreads.length > 0) {
      return apiThreads.map((t) => ({
        thread_id: t.thread_id,
        topic_title: t.topic,
        // Synthesize anonymous participant slugs (the API only returns count).
        participant_ids: Array.from({ length: Math.min(4, t.participant_count) }, (_, i) => `p${i + 1}`),
        message_count: t.message_count,
        // Sentiment summary instead of timestamp — the API doesn't expose
        // a created_at, and avg_sentiment is the most useful at-a-glance signal.
        relative_time: `${t.avg_sentiment >= 0 ? "+" : ""}${t.avg_sentiment.toFixed(2)} avg`,
      }));
    }
    return derivedConversations;
  }, [apiThreads, derivedConversations]);

  // "Demo" no longer means "mock data" — it means "no step data has arrived
  // AND no real threads exist, so the opinion page is showing an empty state."
  const isDemo = derivedClusters.length === 0 && apiThreads.length === 0;

  const sentColor = sentimentTextClass(meta.sentiment);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-[var(--background)]">
      {/* Nav */}
      <PageNav
        breadcrumbs={[
          { label: simulation?.name ?? "Simulation", href: "/projects/p1" },
          { label: meta.name.replace("Community ", ""), href: `/opinions` },
          { label: "Opinion", tooltipTerm: "pageCommunityOpinion" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <span
              className="text-xs px-2 py-0.5 rounded-full border"
              style={{
                backgroundColor: `${meta.color}33`,
                color: meta.color,
                borderColor: `${meta.color}4d`,
              }}
            >
              Level 2 Community
            </span>
            <button
              aria-label="Settings"
              className="p-1.5 rounded-md hover:bg-[var(--secondary)] text-[var(--muted-foreground)]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
        }
      />

      {/* Header */}
      <div className="px-8 py-5 border-b border-[var(--border)]">
        <div className="flex items-center gap-3 mb-2">
          <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
          <h1
            className="text-2xl font-semibold font-display text-[var(--foreground)]"
          >
            {meta.name}
          </h1>
          <span className="text-sm text-[var(--muted-foreground)]">
            {meta.agents.toLocaleString()} agents
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <span className={sentColor}>
            Sentiment {meta.sentiment > 0 ? "+" : ""}
            {meta.sentiment.toFixed(2)}
          </span>
          <span className="text-[var(--muted-foreground)]">Conversations {meta.conversations}</span>
          <span className="text-[var(--muted-foreground)]">Positive {meta.positive_pct}%</span>
        </div>
      </div>

      {/* Demo data banner */}
      {isDemo && (
        <div className="mx-8 mt-4 px-4 py-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-600 text-sm">
          Showing demo data. Run a simulation to see real results.
        </div>
      )}

      {/* EliteLLM synthesised narrative (on-demand) */}
      <EliteLLMNarrativePanel
        simulationId={simId}
        communityId={communityId ?? null}
      />


      {/* Body: 2 columns */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Opinion Clusters */}
        <div className="flex-1 overflow-y-auto px-8 py-5 border-r border-[var(--border)]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[var(--foreground)] inline-flex items-center gap-1.5">
              Opinion Clusters
              <HelpTooltip term="opinionClusters" size="sm" />
            </h2>
            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="text-xs bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] rounded-md px-2 py-1"
            >
              <option value="mentioned">Top Mentioned Topics</option>
              <option value="contested">Most Contested</option>
              <option value="newest">Newest</option>
            </select>
          </div>

          <div className="flex flex-col gap-3">
            {clusters.map((cl) => (
              <div
                key={cl.cluster_id}
                className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-5 hover:border-[var(--muted-foreground)] transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-semibold text-[var(--foreground)]">{cl.topic_name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--muted-foreground)]">
                    {cl.agent_count} agents
                  </span>
                </div>
                <p className="text-xs text-[var(--muted-foreground)] mb-3">{cl.description}</p>

                {/* Stance percentages */}
                <div className="flex items-center gap-4 text-xs mb-2">
                  <span className="text-[var(--sentiment-positive)]">Support {cl.stances.support}%</span>
                  <span className="text-[var(--muted-foreground)]">Neutral {cl.stances.neutral}%</span>
                  <span className="text-[var(--destructive)]">Oppose {cl.stances.oppose}%</span>
                </div>
                <StanceBar stances={cl.stances} />
              </div>
            ))}
          </div>
        </div>

        {/* Right: Recent Conversations */}
        <div className="overflow-y-auto py-5 px-6" style={{ width: 460 }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[var(--foreground)] inline-flex items-center gap-1.5">
              Recent Conversations
              <HelpTooltip term="recentConversations" size="sm" />
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--muted-foreground)]">
              {conversations.length}
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {conversations.map((conv) => (
              <button
                key={conv.thread_id}
                onClick={() => navigate(`/opinions/${communityId}/thread/${conv.thread_id}`)}
                className="w-full text-left bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 hover:bg-[var(--secondary)] transition-colors"
              >
                <h3 className="text-sm font-medium text-[var(--foreground)] mb-2">
                  {conv.topic_title}
                </h3>
                <div className="flex items-center gap-3">
                  {/* Agent avatars */}
                  <div className="flex -space-x-2">
                    {conv.participant_ids.slice(0, 3).map((id) => (
                      <div
                        key={id}
                        className="w-6 h-6 rounded-full bg-[var(--secondary)] border-2 border-[var(--card)] flex items-center justify-center text-[8px] text-[var(--muted-foreground)]"
                        title={id}
                      >
                        {id.slice(0, 2)}
                      </div>
                    ))}
                    {conv.participant_ids.length > 3 && (
                      <div className="w-6 h-6 rounded-full bg-[var(--secondary)] border-2 border-[var(--card)] flex items-center justify-center text-[8px] text-[var(--muted-foreground)]">
                        +{conv.participant_ids.length - 3}
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {conv.message_count} messages
                  </span>
                  <span className="text-xs text-[var(--muted-foreground)] ml-auto">
                    {conv.relative_time}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
