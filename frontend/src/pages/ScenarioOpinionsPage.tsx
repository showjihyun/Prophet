/**
 * ScenarioOpinionsPage — Scenario-wide opinion landscape (UI-13).
 * @spec docs/spec/ui/UI_13_SCENARIO_OPINIONS.md
 */
import { useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";

/* ------------------------------------------------------------------ */
/* Mock Data                                                           */
/* ------------------------------------------------------------------ */

const MOCK_SUMMARY = {
  avg_sentiment: +0.34,
  polarization: 0.72,
  total_conversations: 1247,
  active_cascades: 847,
  day: 47,
  total_agents: 10000,
  community_count: 5,
};

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

const MOCK_COMMUNITIES: CommunityOpinion[] = [
  {
    community_id: "alpha",
    community_name: "Community Alpha",
    agent_count: 2148,
    avg_sentiment: 0.52,
    conversation_count: 312,
    dominant_stance: "positive",
    dominant_pct: 67,
    sentiment_distribution: { positive: 67, neutral: 21, negative: 12 },
    color: "var(--community-alpha)",
  },
  {
    community_id: "beta",
    community_name: "Community Beta",
    agent_count: 1808,
    avg_sentiment: 0.41,
    conversation_count: 256,
    dominant_stance: "positive",
    dominant_pct: 58,
    sentiment_distribution: { positive: 58, neutral: 27, negative: 15 },
    color: "var(--community-beta)",
  },
  {
    community_id: "gamma",
    community_name: "Community Gamma",
    agent_count: 1414,
    avg_sentiment: -0.16,
    conversation_count: 289,
    dominant_stance: "mixed",
    dominant_pct: 42,
    sentiment_distribution: { positive: 30, neutral: 42, negative: 28 },
    color: "var(--community-gamma)",
  },
  {
    community_id: "delta",
    community_name: "Community Delta",
    agent_count: 998,
    avg_sentiment: -0.35,
    conversation_count: 194,
    dominant_stance: "negative",
    dominant_pct: 36,
    sentiment_distribution: { positive: 22, neutral: 42, negative: 36 },
    color: "var(--community-delta)",
  },
  {
    community_id: "bridge",
    community_name: "Bridge Agents",
    agent_count: 1308,
    avg_sentiment: 0.05,
    conversation_count: 182,
    dominant_stance: "mixed",
    dominant_pct: 38,
    sentiment_distribution: { positive: 31, neutral: 38, negative: 31 },
    color: "var(--community-bridge)",
  },
];

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
  const sentimentColor =
    c.avg_sentiment > 0.1
      ? "text-[var(--sentiment-positive)]"
      : c.avg_sentiment < -0.1
        ? "text-[var(--destructive)]"
        : "text-[var(--muted-foreground)]";

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
        className="text-sm text-[var(--community-alpha)] hover:underline self-start mt-1"
      >
        View Community
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ScenarioOpinionsPage() {
  const navigate = useNavigate();
  const s = MOCK_SUMMARY;

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[var(--background)]">
      {/* Nav */}
      <PageNav
        breadcrumbs={[
          { label: "Korea Election 2026", href: "/projects/p1" },
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
            className="text-2xl font-semibold text-[var(--foreground)] mb-1"
            style={{ fontFamily: "'Instrument Serif', serif" }}
          >
            Scenario Opinion Landscape
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Day {s.day} &middot; {s.total_agents.toLocaleString()} agents &middot;{" "}
            {s.community_count} communities
          </p>
        </div>

        {/* 4 Stat cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Avg Sentiment"
            value={`+${s.avg_sentiment.toFixed(2)}`}
            change="+0.08 from yesterday"
            changeType="positive"
          />
          <StatCard
            label="Polarization"
            value={s.polarization.toFixed(2)}
            change="High"
            changeType="negative"
          />
          <StatCard
            label="Total Conversations"
            value={s.total_conversations.toLocaleString()}
            change="+124 today"
            changeType="positive"
          />
          <StatCard
            label="Active Cascades"
            value={s.active_cascades.toLocaleString()}
            change="12 new"
            changeType="neutral"
          />
        </div>

        {/* Section title */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Community Opinion Breakdown
          </h2>
          <button className="text-sm px-3 py-1.5 rounded-md border border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors">
            Data-driven Map vs Faction
          </button>
        </div>

        {/* Community cards grid */}
        <div className="grid grid-cols-3 gap-4">
          {MOCK_COMMUNITIES.map((c) => (
            <CommunityOpinionCard
              key={c.community_id}
              c={c}
              onView={() => navigate(`/opinions/${c.community_id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
