/**
 * CommunitiesDetailPage — Communities overview with cards and connection matrix.
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";
import { apiClient, type CommunityInfo } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

const COMMUNITIES = [
  {
    id: "alpha",
    name: "Alpha Community",
    color: "var(--community-alpha)",
    agents: 1500,
    sentiment: { positive: 62, neutral: 25, negative: 13 },
    influencers: [
      { id: "A-0042", score: 98.2 },
      { id: "A-0187", score: 91.5 },
      { id: "A-0334", score: 87.1 },
    ],
    emotions: { interest: 35, trust: 30, skepticism: 15, excitement: 20 },
    status: "High" as const,
  },
  {
    id: "beta",
    name: "Beta Community",
    color: "var(--community-beta)",
    agents: 1200,
    sentiment: { positive: 55, neutral: 30, negative: 15 },
    influencers: [
      { id: "B-0091", score: 94.7 },
      { id: "B-0203", score: 88.3 },
      { id: "B-0112", score: 82.6 },
    ],
    emotions: { interest: 25, trust: 40, skepticism: 20, excitement: 15 },
    status: "Very High" as const,
  },
  {
    id: "gamma",
    name: "Gamma Community",
    color: "var(--community-gamma)",
    agents: 1100,
    sentiment: { positive: 40, neutral: 35, negative: 25 },
    influencers: [
      { id: "G-0055", score: 85.9 },
      { id: "G-0178", score: 79.4 },
      { id: "G-0290", score: 74.2 },
    ],
    emotions: { interest: 30, trust: 20, skepticism: 30, excitement: 20 },
    status: "Medium" as const,
  },
  {
    id: "delta",
    name: "Delta Community",
    color: "var(--community-delta)",
    agents: 1400,
    sentiment: { positive: 48, neutral: 32, negative: 20 },
    influencers: [
      { id: "D-0067", score: 92.1 },
      { id: "D-0145", score: 86.8 },
      { id: "D-0223", score: 80.4 },
    ],
    emotions: { interest: 28, trust: 25, skepticism: 22, excitement: 25 },
    status: "High" as const,
  },
  {
    id: "bridge",
    name: "Bridge Community",
    color: "var(--community-bridge)",
    agents: 300,
    sentiment: { positive: 35, neutral: 40, negative: 25 },
    influencers: [
      { id: "BR-0012", score: 96.5 },
      { id: "BR-0034", score: 90.2 },
      { id: "BR-0056", score: 84.7 },
    ],
    emotions: { interest: 20, trust: 15, skepticism: 40, excitement: 25 },
    status: "Low" as const,
  },
];

const CONNECTION_MATRIX: Record<string, Record<string, number>> = {
  alpha: { alpha: 1, beta: 0.78, gamma: 0.45, delta: 0.62, bridge: 0.85 },
  beta: { alpha: 0.78, beta: 1, gamma: 0.55, delta: 0.42, bridge: 0.71 },
  gamma: { alpha: 0.45, gamma: 1, beta: 0.55, delta: 0.68, bridge: 0.52 },
  delta: { alpha: 0.62, beta: 0.42, gamma: 0.68, delta: 1, bridge: 0.59 },
  bridge: { alpha: 0.85, beta: 0.71, gamma: 0.52, delta: 0.59, bridge: 1 },
};

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

const COMMUNITY_META: Record<string, { name: string; color: string }> = {
  A: { name: "Alpha Community", color: "var(--community-alpha)" },
  B: { name: "Beta Community", color: "var(--community-beta)" },
  C: { name: "Gamma Community", color: "var(--community-gamma)" },
  D: { name: "Delta Community", color: "var(--community-delta)" },
  E: { name: "Bridge Community", color: "var(--community-bridge)" },
};

function apiToLocal(c: CommunityInfo): typeof COMMUNITIES[number] {
  const meta = COMMUNITY_META[c.community_id] ?? { name: c.name || c.community_id, color: "var(--muted-foreground)" };
  const sentPos = Math.round(Math.max(0, c.mean_belief) * 100);
  const sentNeg = Math.round(Math.max(0, -c.mean_belief) * 100);
  return {
    id: c.community_id.toLowerCase(),
    name: meta.name,
    color: meta.color,
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
  const latestStep = useSimulationStore((s) => s.steps.length > 0 ? s.steps[s.steps.length - 1] : null);
  const [communities, setCommunities] = useState(COMMUNITIES);

  useEffect(() => {
    if (!simulationId) return;
    apiClient.communities.list(simulationId).then((res) => {
      if (res.communities.length > 0) {
        setCommunities(res.communities.map(apiToLocal));
      }
    }).catch(() => { /* keep mock */ });
  }, [simulationId, latestStep?.step]);

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
        <div className="grid grid-cols-3 gap-4">
          {communities.map((community) => (
            <div
              key={community.id}
              data-testid={`community-card-${community.id}`}
              className="interactive bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
              style={{ borderTopColor: community.color, borderTopWidth: 3 }}
              onClick={() => navigate(`/communities/${community.id}`)}
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-[var(--foreground)]">
                  {community.name}
                </h3>
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full text-white"
                  style={{ backgroundColor: community.color }}
                >
                  {community.agents.toLocaleString()} agents
                </span>
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
                        className="text-[var(--community-alpha)] hover:underline"
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
                      const strength =
                        CONNECTION_MATRIX[row.id]?.[col.id] ?? 0;
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
