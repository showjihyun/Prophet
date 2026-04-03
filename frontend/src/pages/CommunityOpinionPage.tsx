/**
 * CommunityOpinionPage — Community-level opinion clusters + conversations (UI-14).
 * @spec docs/spec/ui/UI_14_COMMUNITY_OPINION.md
 */
import { useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import { apiClient } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

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

const COMMUNITY_META: Record<
  string,
  { name: string; color: string; agents: number; sentiment: number; conversations: number; positive_pct: number }
> = {
  alpha: { name: "Community Alpha", color: "var(--community-alpha)", agents: 2148, sentiment: 0.52, conversations: 312, positive_pct: 67 },
  beta: { name: "Community Beta", color: "var(--community-beta)", agents: 1808, sentiment: 0.41, conversations: 256, positive_pct: 58 },
  gamma: { name: "Community Gamma", color: "var(--community-gamma)", agents: 1414, sentiment: -0.16, conversations: 289, positive_pct: 30 },
  delta: { name: "Community Delta", color: "var(--community-delta)", agents: 998, sentiment: -0.35, conversations: 194, positive_pct: 22 },
  bridge: { name: "Bridge Agents", color: "var(--community-bridge)", agents: 1308, sentiment: 0.05, conversations: 182, positive_pct: 31 },
};

const MOCK_CLUSTERS: ClusterData[] = [
  {
    cluster_id: "c1",
    topic_name: "Election Reform Policy",
    description: "Discussions around progressive electoral reform, proportional representation, and voting system changes.",
    agent_count: 847,
    stances: { support: 62, neutral: 24, oppose: 14 },
  },
  {
    cluster_id: "c2",
    topic_name: "Economic Inequality",
    description: "Debates about wealth distribution, tax policy, and social safety net programs.",
    agent_count: 612,
    stances: { support: 45, neutral: 31, oppose: 24 },
  },
  {
    cluster_id: "c3",
    topic_name: "Climate & Energy Policy",
    description: "Conversations on carbon reduction, renewable energy transitions, and environmental regulations.",
    agent_count: 489,
    stances: { support: 38, neutral: 35, oppose: 27 },
  },
];

const MOCK_CONVERSATIONS: ConversationData[] = [
  {
    thread_id: "t1",
    topic_title: "Debate on progressive taxation reform impact",
    participant_ids: ["A-0042", "B-0091", "A-0187", "G-0055"],
    message_count: 12,
    relative_time: "2h ago",
  },
  {
    thread_id: "t2",
    topic_title: "Economic policy fairness across income brackets",
    participant_ids: ["A-0334", "D-0067", "B-0203"],
    message_count: 8,
    relative_time: "3h ago",
  },
  {
    thread_id: "t3",
    topic_title: "Climate energy transition debate",
    participant_ids: ["G-0178", "A-0042", "B-0091", "D-0145", "G-0055"],
    message_count: 15,
    relative_time: "1h ago",
  },
  {
    thread_id: "t4",
    topic_title: "Electoral transparency and voter access",
    participant_ids: ["A-0187", "B-0112"],
    message_count: 6,
    relative_time: "4h ago",
  },
];

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

export default function CommunityOpinionPage() {
  const { communityId } = useParams<{ communityId: string }>();
  const navigate = useNavigate();
  const simulation = useSimulationStore((st) => st.simulation);
  const steps = useSimulationStore((st) => st.steps);
  const simId = simulation?.simulation_id ?? null;

  // Fetch steps from API if store is empty
  useEffect(() => {
    if (simId && steps.length === 0) {
      apiClient.simulations.getSteps(simId).then((fetched) => {
        const { appendStep } = useSimulationStore.getState();
        for (const s of fetched) appendStep(s);
      }).catch(() => {});
    }
  }, [simId, steps.length]);

  // Derive community meta from store steps
  const derivedMeta = useMemo(() => {
    if (!communityId || steps.length === 0) return null;
    const latestStep = steps[steps.length - 1];
    const cm = latestStep.community_metrics?.[communityId];
    if (!cm) return null;
    const totalAgents = cm.adoption_count > 0 ? Math.round(cm.adoption_count / Math.max(0.001, cm.adoption_rate)) : 0;
    return {
      name: `Community ${communityId}`,
      color: "var(--community-alpha)",
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
      const oppose = Math.round(Math.max(0, (cm?.mean_belief ?? 0) < 0 ? -cm!.mean_belief * 100 : 0));
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
    return steps.slice(-4).reverse().map((step, idx) => ({
      thread_id: `step-thread-${step.step}`,
      topic_title: `Step ${step.step}: ${Object.entries(step.action_distribution ?? {}).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "activity"} dominant (${Math.round(step.adoption_rate * 100)}% adoption)`,
      participant_ids: Object.keys(step.community_metrics ?? {}).slice(0, 4),
      message_count: step.llm_calls_this_step,
      relative_time: `${idx + 1} step${idx > 0 ? "s" : ""} ago`,
    }));
  }, [steps]);

  const meta = derivedMeta ?? COMMUNITY_META[communityId ?? "alpha"] ?? COMMUNITY_META.alpha;
  const clusters = derivedClusters.length > 0 ? derivedClusters : MOCK_CLUSTERS;
  const conversations = derivedConversations.length > 0 ? derivedConversations : MOCK_CONVERSATIONS;

  const sentColor = meta.sentiment > 0.1 ? "text-[var(--sentiment-positive)]" : meta.sentiment < -0.1 ? "text-[var(--destructive)]" : "text-[var(--muted-foreground)]";

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[var(--background)]">
      {/* Nav */}
      <PageNav
        breadcrumbs={[
          { label: "Korea Election 2026", href: "/projects/p1" },
          { label: meta.name.replace("Community ", ""), href: `/opinions` },
          { label: "Opinion" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--community-alpha)]/20 text-[var(--community-alpha)] border border-[var(--community-alpha)]/30">
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
            className="text-2xl font-semibold text-[var(--foreground)]"
            style={{ fontFamily: "'Instrument Serif', serif" }}
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

      {/* Body: 2 columns */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Opinion Clusters */}
        <div className="flex-1 overflow-y-auto px-8 py-5 border-r border-[var(--border)]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[var(--foreground)]">Opinion Clusters</h2>
            <select className="text-xs bg-[var(--secondary)] text-[var(--foreground)] border border-[var(--border)] rounded-md px-2 py-1">
              <option>Top Mentioned Topics</option>
              <option>Most Contested</option>
              <option>Newest</option>
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
            <h2 className="text-base font-semibold text-[var(--foreground)]">Recent Conversations</h2>
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
