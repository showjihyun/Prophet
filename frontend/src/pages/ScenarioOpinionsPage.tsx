/**
 * ScenarioOpinionsPage — Scenario-wide opinion landscape (Level 1).
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-l1
 */
import { useEffect, useMemo, useState, lazy, Suspense } from "react";
import { useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";
import OverallOpinionPanel from "../components/community/OverallOpinionPanel";
import { useSimulationSteps } from "../api/queries";
import { useSimulationStore } from "../store/simulationStore";
import {
  sentimentTextClass,
  formatDelta,
  deltaChangeType,
} from "../utils/sentiment";

const FactionMapView = lazy(() => import("../components/graph/FactionMapView"));

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface CommunityOpinion {
  community_id: string;
  community_name: string;
  agent_count: number;
  avg_sentiment: number;
  conversation_count: number;
  dominant_stance: "positive" | "negative" | "mixed";
  dominant_pct: number;
  sentiment_distribution: { positive: number; neutral: number; negative: number };
  color: string;
}

// MOCK_SUMMARY / MOCK_COMMUNITIES removed — the page renders only real
// data derived from `latestStep` and the simulation store. When no step
// has arrived, an explicit empty state is shown instead of a fabricated
// "10,000 agents / day 47 / 1,247 conversations" snapshot.

/* ------------------------------------------------------------------ */
/* Sentiment Bar                                                       */
/* ------------------------------------------------------------------ */

function SentimentBar({ dist }: { dist: { positive: number; neutral: number; negative: number } }) {
  return (
    <div className="flex h-2 w-full rounded-full overflow-hidden mt-2">
      <div
        className="h-full"
        style={{ width: `${dist.positive}%`, backgroundColor: "var(--sentiment-positive)" }}
      />
      <div
        className="h-full"
        style={{ width: `${dist.neutral}%`, backgroundColor: "var(--sentiment-neutral)" }}
      />
      <div
        className="h-full"
        style={{ width: `${dist.negative}%`, backgroundColor: "var(--sentiment-negative)" }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Community Opinion Card                                              */
/* ------------------------------------------------------------------ */

function CommunityOpinionCard({ c, onView }: { c: CommunityOpinion; onView: () => void }) {
  const sentimentColor = sentimentTextClass(c.avg_sentiment);

  const stanceLabel =
    c.dominant_stance === "positive"
      ? `Positive ${c.dominant_pct}%`
      : c.dominant_stance === "negative"
        ? `Negative ${c.dominant_pct}%`
        : `Mixed ${c.dominant_pct}%`;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg p-5 flex flex-col gap-3 hover:scale-[1.02] transition-transform">
      {/* Name row */}
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: c.color }}
        />
        <span className="font-semibold text-[var(--foreground)]">{c.community_name}</span>
        <span className="text-xs text-[var(--muted-foreground)] ml-auto">
          {c.agent_count.toLocaleString()} agents
        </span>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm">
        <span className={sentimentColor}>
          Sentiment {c.avg_sentiment > 0 ? "+" : ""}
          {c.avg_sentiment.toFixed(2)}
        </span>
        <span className="text-[var(--muted-foreground)]">
          {c.conversation_count} conversations
        </span>
      </div>

      {/* Stance + bar */}
      <div>
        <span className="text-xs text-[var(--muted-foreground)]">{stanceLabel}</span>
        <SentimentBar dist={c.sentiment_distribution} />
      </div>

      {/* Action */}
      <button
        onClick={onView}
        className="text-sm hover:underline self-start mt-1"
        style={{ color: c.color }}
      >
        View Community
      </button>
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

export default function ScenarioOpinionsPage() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((st) => st.simulation);
  const steps = useSimulationStore((st) => st.steps);
  const simId = simulation?.simulation_id ?? null;
  const [viewMode, setViewMode] = useState<"data" | "faction">("data");

  // TanStack Query — bulk hydrate the store once when the live array is empty
  const stepsQuery = useSimulationSteps(steps.length === 0 ? simId : null);
  useEffect(() => {
    if (stepsQuery.data && steps.length === 0) {
      useSimulationStore.getState().setStepsBulk(stepsQuery.data);
    }
  }, [stepsQuery.data, steps.length]);

  // Derive community opinions from the latest step's community_metrics
  const derivedCommunities = useMemo<CommunityOpinion[]>(() => {
    const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;
    if (!latestStep || !latestStep.community_metrics) return [];
    return Object.entries(latestStep.community_metrics).map(([cid, metrics], idx) => {
      const clamped = Math.max(-1, Math.min(1, metrics.mean_belief));
      const positivePct = Math.round(Math.max(0, clamped) * 100);
      const negativePct = Math.round(Math.max(0, -clamped) * 100);
      const neutralPct = 100 - positivePct - negativePct;
      const dominant: CommunityOpinion["dominant_stance"] =
        clamped > 0.1 ? "positive" : clamped < -0.1 ? "negative" : "mixed";
      return {
        community_id: cid,
        community_name: `Community ${cid}`,
        agent_count: metrics.adoption_count > 0 ? Math.round(metrics.adoption_count / Math.max(0.001, metrics.adoption_rate)) : 0,
        avg_sentiment: clamped,
        conversation_count: metrics.new_propagation_count,
        dominant_stance: dominant,
        dominant_pct: dominant === "positive" ? positivePct : dominant === "negative" ? negativePct : neutralPct,
        sentiment_distribution: { positive: positivePct, neutral: Math.max(0, neutralPct), negative: negativePct },
        color: COMMUNITY_COLORS_MAP[idx % 5] ?? "var(--muted-foreground)",
      } satisfies CommunityOpinion;
    });
  }, [steps]);

  const communities = derivedCommunities;

  const derivedSummary = useMemo(() => {
    const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;
    if (!latestStep || !simulation) return null;
    const totalConversations = Object.values(latestStep.community_metrics ?? {}).reduce(
      (acc, m) => acc + m.new_propagation_count, 0,
    );
    return {
      avg_sentiment: latestStep.mean_sentiment,
      polarization: latestStep.sentiment_variance,
      total_conversations: totalConversations,
      active_cascades: Math.round(latestStep.adoption_rate * 1000),
      step: latestStep.step,
      total_agents: Object.values(latestStep.community_metrics ?? {}).reduce(
        (acc, m) => acc + (m.adoption_count > 0 ? Math.round(m.adoption_count / Math.max(0.001, m.adoption_rate)) : 0),
        0,
      ),
      community_count: Object.keys(latestStep.community_metrics ?? {}).length,
    };
  }, [steps, simulation]);

  // Real-data-only: all zeros until a step arrives.
  const s = derivedSummary ?? {
    avg_sentiment: 0,
    polarization: 0,
    total_conversations: 0,
    active_cascades: 0,
    step: 0,
    total_agents: 0,
    community_count: 0,
  };
  const isDemo = derivedCommunities.length === 0;

  // Real prev-vs-current deltas for the 4 stat cards.
  // SPEC: 27_OPINIONS_SPEC.md#opinions-l1-stat (AC-L1-02 / AC-L1-03)
  // When fewer than 2 steps exist, deltas are undefined and the change line
  // is not rendered (StatCard suppresses an absent `change` prop).
  const statDeltas = useMemo(() => {
    if (steps.length < 2) {
      return {
        sentiment: undefined as string | undefined,
        sentimentType: "neutral" as const,
        polarization: undefined as string | undefined,
        polarizationType: "neutral" as const,
        conversations: undefined as string | undefined,
        conversationsType: "neutral" as const,
        cascades: undefined as string | undefined,
        cascadesType: "neutral" as const,
      };
    }
    const prev = steps[steps.length - 2];
    const cur = steps[steps.length - 1];
    const sumProp = (m: typeof prev.community_metrics) =>
      Object.values(m ?? {}).reduce((a, x) => a + x.new_propagation_count, 0);
    const sentDiff = cur.mean_sentiment - prev.mean_sentiment;
    const polDiff = cur.sentiment_variance - prev.sentiment_variance;
    const convDiff = sumProp(cur.community_metrics) - sumProp(prev.community_metrics);
    const casDiff =
      Math.round(cur.adoption_rate * 1000) - Math.round(prev.adoption_rate * 1000);
    return {
      sentiment: formatDelta(sentDiff, "from prev step"),
      sentimentType: deltaChangeType(sentDiff),
      polarization: formatDelta(polDiff, "from prev step"),
      // Inverted: higher polarization is bad news.
      polarizationType: deltaChangeType(polDiff, true),
      conversations: formatDelta(convDiff, "from prev step"),
      conversationsType: deltaChangeType(convDiff),
      cascades: formatDelta(casDiff, "from prev step"),
      cascadesType: deltaChangeType(casDiff),
    };
  }, [steps]);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-[var(--background)]">
      {/* Nav */}
      <PageNav
        breadcrumbs={[
          { label: simulation?.name ?? "Simulation", href: "/projects/p1" },
          { label: "Agent Opinion" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)]">
              Level 1
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
            <div className="w-8 h-8 rounded-full bg-[var(--secondary)] border border-[var(--border)]" />
          </div>
        }
      />

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1
            className="text-2xl font-semibold font-display text-[var(--foreground)] mb-1"
          >
            Scenario Opinion Landscape
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Step {s.step} &middot; {s.total_agents.toLocaleString()} agents &middot;{" "}
            {s.community_count} communities
          </p>
        </div>

        {/* Demo data banner */}
        {isDemo && (
          <div className="mb-4 px-4 py-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-600 text-sm">
            Showing demo data. Run a simulation to see real results.
          </div>
        )}

        {/* Cross-community EliteLLM narrative (on-demand) */}
        <div className="mb-6">
          <OverallOpinionPanel simulationId={simId} />
        </div>

        {/* 4 Stat cards — real prev-vs-current deltas (SPEC 27 §4.2) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Avg Sentiment"
            value={`${s.avg_sentiment >= 0 ? "+" : ""}${s.avg_sentiment.toFixed(2)}`}
            change={statDeltas.sentiment}
            changeType={statDeltas.sentimentType}
          />
          <StatCard
            label="Polarization"
            value={s.polarization.toFixed(2)}
            change={statDeltas.polarization}
            changeType={statDeltas.polarizationType}
          />
          <StatCard
            label="Total Conversations"
            value={s.total_conversations.toLocaleString()}
            change={statDeltas.conversations}
            changeType={statDeltas.conversationsType}
          />
          <StatCard
            label="Active Cascades"
            value={s.active_cascades.toLocaleString()}
            change={statDeltas.cascades}
            changeType={statDeltas.cascadesType}
          />
        </div>

        {/* Section title */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Community Opinion Breakdown
          </h2>
          <button
            onClick={() => setViewMode(viewMode === "data" ? "faction" : "data")}
            className="text-sm px-3 py-1.5 rounded-md border border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            {viewMode === "data" ? "Switch to Faction View" : "Switch to Data-driven Map"}
          </button>
        </div>

        {/* View: Data-driven Map (cards) or Faction View (graph) */}
        {viewMode === "data" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {communities.map((c) => (
              <CommunityOpinionCard
                key={c.community_id}
                c={c}
                onView={() => navigate(`/opinions/${c.community_id}`)}
              />
            ))}
          </div>
        ) : (
          <Suspense fallback={<div className="flex items-center justify-center h-[500px] text-sm text-[var(--muted-foreground)]">Loading Faction View...</div>}>
            <FactionMapView
              communities={communities}
              onCommunityClick={(cid) => navigate(`/opinions/${cid}`)}
            />
          </Suspense>
        )}
      </div>
    </div>
  );
}
