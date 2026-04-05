/**
 * AgentDetailPage — Agent profile, personality, activity chart, and interactions.
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md
 */
import { useState, useMemo, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient, type AgentDetail, type MemoryRecord } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

// Community color map for deriving connection colors from graph data
const COMMUNITY_COLORS: Record<string, string> = {
  A: "#3b82f6",
  B: "#22c55e",
  C: "#f97316",
  D: "#a855f7",
  E: "#ef4444",
  Alpha: "#3b82f6",
  Beta: "#22c55e",
  Gamma: "#f97316",
  Delta: "#a855f7",
  Bridge: "#ef4444",
};
import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import PageNav from "../components/shared/PageNav";
import AgentInterveneModal from "../components/shared/AgentInterveneModal";
import EgoGraph from "../components/graph/EgoGraph";

const MOCK_AGENT = {
  id: "A-0042",
  agentNumber: 3847,
  community: "Alpha",
  communityColor: "var(--community-alpha)",
  influence: 98.2,
  connections: 247,
  subscribers: 12,
  trust: 0.87,
  personality: {
    Openness: 78,
    Skepticism: 42,
    Adaptability: 65,
    Advocacy: 88,
    "Trust/Safety": 71,
  },
  memorySummary:
    "Agent has been a consistent advocate for the primary message within the Alpha community. Recent interactions show increasing trust with Bridge community members. Memory includes 34 episodic events, 12 semantic concepts related to brand messaging, and active social connections with 5 high-influence peers.",
};

const SENTIMENT_DATA = [
  { day: "D41", positive: 60, negative: 20 },
  { day: "D42", positive: 70, negative: 15 },
  { day: "D43", positive: 55, negative: 30 },
  { day: "D44", positive: 80, negative: 10 },
  { day: "D45", positive: 65, negative: 25 },
  { day: "D46", positive: 75, negative: 18 },
  { day: "D47", positive: 85, negative: 12 },
];

interface Interaction {
  target: string;
  type: "Share" | "Reply" | "Mention" | "Influence";
  sentiment: "Positive" | "Neutral" | "Negative";
  message: string;
  time: string;
}

const MOCK_INTERACTIONS: Interaction[] = [
  { target: "B-0091", type: "Share", sentiment: "Positive", message: "Great insight on the campaign strategy, sharing with my network...", time: "2h ago" },
  { target: "A-0187", type: "Reply", sentiment: "Positive", message: "I agree with the approach. The data supports this direction.", time: "4h ago" },
  { target: "BR-0012", type: "Influence", sentiment: "Neutral", message: "Bridging the gap between Alpha and Beta communities on this topic.", time: "6h ago" },
  { target: "D-0067", type: "Mention", sentiment: "Positive", message: "Referenced Agent D-0067's analysis in the community discussion.", time: "8h ago" },
  { target: "G-0055", type: "Share", sentiment: "Negative", message: "Disagreeing with the Gamma community's stance on this issue.", time: "12h ago" },
  { target: "A-0334", type: "Reply", sentiment: "Positive", message: "Excellent follow-up on yesterday's interaction chain.", time: "1d ago" },
];

const SENTIMENT_STYLES: Record<string, React.CSSProperties> = {
  Positive: { backgroundColor: "color-mix(in srgb, var(--sentiment-positive) 15%, transparent)", color: "var(--sentiment-positive)" },
  Neutral: { backgroundColor: "color-mix(in srgb, var(--sentiment-neutral) 15%, transparent)", color: "var(--sentiment-neutral)" },
  Negative: { backgroundColor: "color-mix(in srgb, var(--sentiment-negative) 15%, transparent)", color: "var(--sentiment-negative)" },
};

const TYPE_STYLES: Record<string, React.CSSProperties> = {
  Share: { color: "var(--community-alpha)" },
  Reply: { color: "var(--community-beta)" },
  Mention: { color: "var(--community-gamma)" },
  Influence: { color: "var(--community-delta)" },
};

// ---------------------------------------------------------------------------
// Mock connections data for the Connections tab sidebar
// ---------------------------------------------------------------------------
interface ConnectionItem {
  id: string;
  name: string;
  community: string;
  color: string;
  trust: number;
  influence: number;
}

const MOCK_CONNECTIONS: ConnectionItem[] = [
  { id: "a1", name: "Agent #1043", community: "Alpha", color: "#3b82f6", trust: 0.92, influence: 0.85 },
  { id: "a2", name: "Agent #4214", community: "Beta", color: "#22c55e", trust: 0.87, influence: 0.72 },
  { id: "a3", name: "Agent #0891", community: "Alpha", color: "#3b82f6", trust: 0.84, influence: 0.68 },
  { id: "a4", name: "Agent #2301", community: "Gamma", color: "#f97316", trust: 0.79, influence: 0.61 },
  { id: "a5", name: "Agent #7782", community: "Delta", color: "#a855f7", trust: 0.75, influence: 0.55 },
  { id: "a6", name: "Agent #0012", community: "Bridge", color: "#ef4444", trust: 0.73, influence: 0.90 },
  { id: "a7", name: "Agent #5567", community: "Beta", color: "#22c55e", trust: 0.71, influence: 0.48 },
  { id: "a8", name: "Agent #3344", community: "Alpha", color: "#3b82f6", trust: 0.68, influence: 0.52 },
];

// ---------------------------------------------------------------------------
// Mock messages data for the Messages tab
// ---------------------------------------------------------------------------
interface MessageItem {
  id: string;
  type: "share" | "comment" | "repost" | "adopt";
  content: string;
  timestamp: string;
  sentiment: "positive" | "neutral" | "negative";
  reach: number;
  reactions: { like: number; comment: number; repost: number };
  replyTo?: string;
}

const MOCK_MESSAGES: MessageItem[] = [
  {
    id: "m1",
    type: "share",
    content: "The AI camera phone looks promising. Battery specs need verification though.",
    timestamp: "2m ago",
    sentiment: "positive",
    reach: 47,
    reactions: { like: 12, comment: 3, repost: 2 },
  },
  {
    id: "m2",
    type: "comment",
    content: "Responding to Agent #1043: I agree the camera quality is competitive, but the price point concerns me.",
    timestamp: "15m ago",
    sentiment: "neutral",
    reach: 23,
    reactions: { like: 5, comment: 1, repost: 0 },
    replyTo: "Agent #1043",
  },
  {
    id: "m3",
    type: "repost",
    content: "RT @Agent #4214: This campaign is gaining traction in the Beta community. Watch the cascade.",
    timestamp: "32m ago",
    sentiment: "positive",
    reach: 89,
    reactions: { like: 24, comment: 7, repost: 15 },
    replyTo: "Agent #4214",
  },
  {
    id: "m4",
    type: "adopt",
    content: "Decision: Adopting the product. Key factor: trusted recommendation from Agent #0592.",
    timestamp: "1h ago",
    sentiment: "positive",
    reach: 12,
    reactions: { like: 3, comment: 0, repost: 1 },
  },
  {
    id: "m5",
    type: "comment",
    content: "I'm skeptical about the marketing claims. Has anyone actually tested the AI features?",
    timestamp: "2h ago",
    sentiment: "negative",
    reach: 56,
    reactions: { like: 8, comment: 12, repost: 4 },
  },
  {
    id: "m6",
    type: "share",
    content: "Sharing expert analysis: The technology behind the AI camera is solid, based on the review from Community Delta.",
    timestamp: "3h ago",
    sentiment: "positive",
    reach: 134,
    reactions: { like: 31, comment: 9, repost: 18 },
  },
];

const TABS = ["Activity", "Connections", "Messages"] as const;

const COMMUNITY_ID_TO_NAME: Record<string, { name: string; color: string }> = {
  A: { name: "Alpha", color: "var(--community-alpha)" },
  B: { name: "Beta", color: "var(--community-beta)" },
  C: { name: "Gamma", color: "var(--community-gamma)" },
  D: { name: "Delta", color: "var(--community-delta)" },
  E: { name: "Bridge", color: "var(--community-bridge)" },
};

function apiToAgent(a: AgentDetail) {
  const comm = COMMUNITY_ID_TO_NAME[a.community_id] ?? { name: a.community_id, color: "var(--muted-foreground)" };
  return {
    id: a.agent_id,
    agentNumber: a.agent_id.replace(/\D/g, "").slice(-4) || a.agent_id.slice(0, 6),
    community: comm.name,
    communityColor: comm.color,
    influence: Math.round(a.influence_score * 1000) / 10,
    connections: 0,
    subscribers: 0,
    trust: a.emotion?.trust ?? 0,
    personality: Object.fromEntries(
      Object.entries(a.personality ?? {}).map(([k, v]) => [k.charAt(0).toUpperCase() + k.slice(1), Math.round(v * 100)]),
    ),
    memorySummary: a.memories.length > 0
      ? a.memories.slice(0, 3).map((m) => m.content ?? String(m)).join(" | ")
      : MOCK_AGENT.memorySummary,
  };
}

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const steps = useSimulationStore((s) => s.steps);
  const status = useSimulationStore((s) => s.status);
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("Activity");
  const [interveneOpen, setInterveneOpen] = useState(false);
  const [connSearch, setConnSearch] = useState("");
  const [msgFilter, setMsgFilter] = useState("all");

  const [agent, setAgent] = useState({ ...MOCK_AGENT, id: agentId ?? MOCK_AGENT.id });
  // Connections: start with MOCK_CONNECTIONS as fallback; replaced when network data loads
  const [connections, setConnections] = useState<ConnectionItem[]>(MOCK_CONNECTIONS);

  // Fetch real agent data from API
  useEffect(() => {
    if (!simulationId || !agentId) return;
    apiClient.agents.get(simulationId, agentId).then((res) => {
      setAgent(apiToAgent(res));
    }).catch(() => {
      setAgent({ ...MOCK_AGENT, id: agentId });
    });
  }, [simulationId, agentId]);

  // Fetch real connections from network graph
  useEffect(() => {
    if (!simulationId || !agentId) return;
    apiClient.network.get(simulationId).then((graph) => {
      const connected = graph.edges
        .filter((e) => String(e.data.source) === agentId || String(e.data.target) === agentId)
        .slice(0, 20);
      const conns: ConnectionItem[] = connected.map((e, i) => {
        const peerId =
          String(e.data.source) === agentId
            ? String(e.data.target)
            : String(e.data.source);
        const peerNode = graph.nodes.find((n) => String(n.data.id) === peerId);
        const community = (peerNode?.data.community as string) ?? "Unknown";
        return {
          id: `c${i}`,
          name: `Agent ${peerId}`,
          community,
          color: COMMUNITY_COLORS[community] ?? "#888",
          trust: (e.data.weight as number) ?? 0.5,
          influence: (peerNode?.data.influence_score as number) ?? 0.5,
        };
      });
      if (conns.length > 0) setConnections(conns);
    }).catch(() => {});
  }, [simulationId, agentId]);

  // Fetch real agent messages (memory records) from API
  const [apiMessages, setApiMessages] = useState<MessageItem[]>([]);
  useEffect(() => {
    if (!simulationId || !agentId) return;
    apiClient.agents.getMemory(simulationId, agentId).then((res) => {
      const msgs: MessageItem[] = (res.memories ?? []).map((m: MemoryRecord, i: number) => {
        const type: MessageItem["type"] =
          m.memory_type === "episodic" ? "share" :
          m.memory_type === "semantic" ? "comment" : "share";
        const sentiment: MessageItem["sentiment"] =
          m.importance > 0.6 ? "positive" :
          m.importance < 0.3 ? "negative" : "neutral";
        return {
          id: `mem-${i}`,
          type,
          content: m.content,
          timestamp: m.timestamp != null ? `Step ${m.timestamp}` : "—",
          sentiment,
          reach: Math.round(m.importance * 100),
          reactions: { like: 0, comment: 0, repost: 0 },
          replyTo: m.source_agent_id ? `Agent ${m.source_agent_id}` : undefined,
        };
      });
      if (msgs.length > 0) setApiMessages(msgs);
    }).catch(() => {});
  }, [simulationId, agentId]);

  // Derive sentiment chart data from store steps (last 7), fallback to SENTIMENT_DATA
  const sentimentData = useMemo(() => {
    if (steps.length === 0) return SENTIMENT_DATA;
    return steps.slice(-7).map((s) => ({
      day: `D${s.step}`,
      positive: Math.max(0, s.mean_sentiment) * 100,
      negative: Math.max(0, -s.mean_sentiment) * 100,
    }));
  }, [steps]);

  const filteredConnections = useMemo(
    () =>
      connections.filter(
        (c) =>
          c.name.toLowerCase().includes(connSearch.toLowerCase()) ||
          c.community.toLowerCase().includes(connSearch.toLowerCase()),
      ),
    [connections, connSearch],
  );

  // Derive interactions from step history — each step where action_distribution changes
  const derivedInteractions = useMemo<Interaction[]>(() => {
    if (steps.length === 0) return [];
    const ACTION_TYPE_MAP: Record<string, Interaction["type"]> = {
      share: "Share",
      repost: "Share",
      comment: "Reply",
      reply: "Reply",
      follow: "Influence",
      mention: "Mention",
      adopt: "Influence",
    };
    return steps.slice(-6).reverse().map((step): Interaction => {
      const topAction = Object.entries(step.action_distribution ?? {})
        .sort((a, b) => b[1] - a[1])[0];
      const actionKey = topAction?.[0] ?? "view";
      const type: Interaction["type"] = ACTION_TYPE_MAP[actionKey] ?? "Influence";
      const sentiment: Interaction["sentiment"] =
        step.mean_sentiment > 0.1 ? "Positive" : step.mean_sentiment < -0.1 ? "Negative" : "Neutral";
      const topCommunity = Object.keys(step.community_metrics ?? {})[0] ?? "—";
      return {
        target: `Community-${topCommunity}`,
        type,
        sentiment,
        message: `Step ${step.step}: ${actionKey} action dominant (${Math.round((topAction?.[1] ?? 0) * 10)}% of agents). Adoption: ${Math.round(step.adoption_rate * 100)}%.`,
        time: `Step ${step.step}`,
      };
    });
  }, [steps]);

  const interactions = derivedInteractions.length > 0 ? derivedInteractions : MOCK_INTERACTIONS;

  const messagesSource = apiMessages.length > 0 ? apiMessages : MOCK_MESSAGES;
  const filteredMessages = useMemo(
    () =>
      msgFilter === "all"
        ? messagesSource
        : messagesSource.filter((m) => m.type === msgFilter),
    [msgFilter, messagesSource],
  );

  return (
    <div
      data-testid="agent-detail-page"
      className="min-h-screen bg-[var(--muted)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Simulation", href: "/" },
          { label: agent.community },
          { label: `Agent #${agent.agentNumber}`, testId: "agent-breadcrumb" },
        ]}
        actions={
          <button
            onClick={() => setInterveneOpen(true)}
            disabled={status !== 'paused'}
            title={status !== 'paused' ? "Pause simulation to intervene" : undefined}
            className="h-9 px-4 text-sm font-medium text-white rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ backgroundColor: 'var(--sentiment-positive)' }}
          >
            Intervene
          </button>
        }
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Agent Profile */}
        <aside className="w-[360px] shrink-0 border-r border-[var(--border)] bg-[var(--card)] overflow-y-auto p-6 flex flex-col gap-6">
          {/* Avatar */}
          <div className="flex flex-col items-center gap-3">
            <div
              data-testid="agent-avatar"
              className="w-20 h-20 rounded-full flex items-center justify-center text-white text-xl font-bold"
              style={{
                backgroundColor: agent.communityColor,
                boxShadow: `0 0 0 3px white, 0 0 0 6px ${agent.communityColor}`,
              }}
            >
              {agent.agentNumber}
            </div>
            <h2 data-testid="agent-id-heading" className="text-2xl font-bold font-display text-[var(--foreground)]">
              Agent #{agent.agentNumber}
            </h2>
            <span data-testid="community-badge" className="inline-flex items-center gap-1.5 text-sm bg-[var(--secondary)] px-3 py-1 rounded-full">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: agent.communityColor }}
              />
              {agent.community}
            </span>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Influence", value: agent.influence },
              { label: "Connections", value: agent.connections },
              { label: "Subscribers", value: agent.subscribers },
              { label: "Trust Level", value: agent.trust },
            ].map((stat) => (
              <div
                key={stat.label}
                className="bg-[var(--muted)] rounded-lg p-3 text-center"
              >
                <div className="text-xl font-bold text-[var(--foreground)]">
                  {stat.value}
                </div>
                <div className="text-xs text-[var(--muted-foreground)]">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Personality Traits */}
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
              Personality Traits
            </h3>
            <div className="space-y-3">
              {Object.entries(agent.personality).map(([trait, value]) => (
                <div key={trait} className="flex items-center gap-2">
                  <span className="text-[13px] text-[var(--muted-foreground)] w-24 shrink-0">
                    {trait}
                  </span>
                  <div data-testid={`trait-bar-${trait.toLowerCase().replace(/\//g, '-')}`} className="flex-1 h-2 rounded-full bg-[var(--muted)] overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${value}%`, backgroundColor: agent.communityColor }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-[var(--foreground)] w-10 text-right">
                    {value}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Memory Summary */}
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">
              Memory Summary
            </h3>
            <div data-testid="memory-summary" className="bg-[var(--muted)] rounded-lg p-3 text-[13px] text-[var(--muted-foreground)] leading-relaxed border border-[var(--border)]">
              {agent.memorySummary}
            </div>
          </div>
        </aside>

        {/* Right Panel - Activity & Interactions */}
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {/* Tab Bar */}
          <div role="tablist" className="flex border-b border-[var(--border)]">
            {TABS.map((tab) => (
              <button
                key={tab}
                role="tab"
                aria-selected={activeTab === tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors relative ${
                  activeTab === tab
                    ? "text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--foreground)]" />
                )}
              </button>
            ))}
          </div>

          {activeTab === "Activity" && (
            <>
              {/* Sentiment Over Time */}
              <div data-testid="sentiment-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
                <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4">
                  Sentiment Over Time
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={sentimentData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <Tooltip />
                    <Area type="monotone" dataKey="positive" fill="var(--sentiment-positive)" fillOpacity={0.1} stroke="none" />
                    <Area type="monotone" dataKey="negative" fill="var(--sentiment-negative)" fillOpacity={0.1} stroke="none" />
                    <Line type="monotone" dataKey="positive" stroke="var(--sentiment-positive)" strokeWidth={2} dot={false} name="Positive" />
                    <Line type="monotone" dataKey="negative" stroke="var(--sentiment-negative)" strokeWidth={2} dot={false} name="Negative" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Recent Interactions */}
              <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm overflow-hidden">
                <div className="p-4 border-b border-[var(--border)]">
                  <h3 className="text-sm font-semibold text-[var(--foreground)]">
                    Recent Interactions
                  </h3>
                </div>
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-[var(--border)] bg-[var(--muted)]">
                      <th className="text-left px-4 py-3 font-semibold text-[var(--muted-foreground)]">
                        Target Agent
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[var(--muted-foreground)]">
                        Type
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[var(--muted-foreground)]">
                        Sentiment
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[var(--muted-foreground)]">
                        Message Preview
                      </th>
                      <th className="text-right px-4 py-3 font-semibold text-[var(--muted-foreground)]">
                        Time
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {interactions.map((interaction, i) => (
                      <tr
                        key={i}
                        className="border-b border-[var(--border)] hover:bg-[var(--accent)] transition-colors"
                      >
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              navigate(`/agents/${interaction.target}`)
                            }
                            className="text-[var(--community-alpha)] hover:underline font-medium"
                          >
                            {interaction.target}
                          </button>
                        </td>
                        <td
                          className="px-4 py-3 font-medium"
                          style={TYPE_STYLES[interaction.type]}
                        >
                          {interaction.type}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className="text-[11px] font-medium px-2 py-0.5 rounded-full"
                            style={SENTIMENT_STYLES[interaction.sentiment]}
                          >
                            {interaction.sentiment}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[var(--muted-foreground)] max-w-xs truncate">
                          {interaction.message}
                        </td>
                        <td className="text-right px-4 py-3 text-[var(--muted-foreground)]">
                          {interaction.time}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {activeTab === "Connections" && (
            <div className="flex gap-0 flex-1 min-h-[500px]">
              {/* Ego Graph */}
              <div
                className="flex-1 relative rounded-lg overflow-hidden"
                style={{
                  background:
                    "radial-gradient(ellipse at center, #0f172a 0%, #020617 100%)",
                }}
              >
                <EgoGraph agentId={String(agent.agentNumber)} />
                <div className="absolute top-3 left-4 z-10 pointer-events-none">
                  <span className="text-white text-sm font-semibold">
                    Ego Network Graph
                  </span>
                  <span className="text-[var(--muted-foreground)] text-xs block">
                    {agent.connections} connections found
                  </span>
                </div>
              </div>
              {/* Top Connections Sidebar */}
              <div
                className="w-[280px] shrink-0 border-l bg-[var(--card)] overflow-y-auto p-4 flex flex-col gap-3"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-[var(--foreground)]">
                    Top Connections
                  </span>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {connections.length}
                  </span>
                </div>
                <input
                  placeholder="Search connections..."
                  value={connSearch}
                  onChange={(e) => setConnSearch(e.target.value)}
                  className="rounded-md border px-3 py-1.5 text-sm w-full"
                  style={{ borderColor: "var(--input)" }}
                />
                <div className="flex flex-col gap-2 overflow-y-auto flex-1">
                  {filteredConnections.map((conn) => (
                    <button
                      key={conn.id}
                      onClick={() =>
                        navigate(`/agents/${conn.name.replace("Agent #", "")}`)
                      }
                      className="interactive flex items-center gap-3 p-2 rounded-md hover:bg-[var(--accent)] text-left transition-colors"
                    >
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                        style={{ backgroundColor: conn.color }}
                      >
                        {conn.name.slice(-4)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate text-[var(--foreground)]">
                          {conn.name}
                        </div>
                        <div className="text-xs text-[var(--muted-foreground)]">
                          {conn.community} &middot; Trust: {conn.trust.toFixed(2)}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xs font-semibold text-[var(--foreground)]">
                          {conn.influence.toFixed(2)}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "Messages" && (
            <div className="flex flex-col gap-4">
              {/* Demo data notice — only shown when using mock data */}
              {apiMessages.length === 0 && (
                <div className="px-4 py-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-600 text-sm">
                  Showing sample messages. Real agent messages will appear during simulation.
                </div>
              )}

              {/* Header with stats */}
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--foreground)]">Message History</h3>
                <span className="text-xs text-[var(--muted-foreground)]">{filteredMessages.length} messages</span>
              </div>

              {/* Filter bar */}
              <div className="flex gap-2">
                {(["all", "share", "comment", "repost", "adopt"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setMsgFilter(type)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      msgFilter === type
                        ? "bg-[var(--foreground)] text-[var(--card)]"
                        : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
                    }`}
                  >
                    {type === "all" ? "All" : type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>

              {/* Message list */}
              <div className="flex flex-col gap-3">
                {filteredMessages.map((msg) => (
                  <div key={msg.id} className="rounded-lg border border-[var(--border)] p-4 bg-[var(--card)]">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {/* Action type badge */}
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            msg.type === "share"
                              ? "bg-[var(--community-alpha)]/20 text-[var(--community-alpha)]"
                              : msg.type === "comment"
                                ? "bg-[var(--community-delta)]/20 text-[var(--community-delta)]"
                                : msg.type === "repost"
                                  ? "bg-[var(--community-gamma)]/20 text-[var(--community-gamma)]"
                                  : "bg-[var(--sentiment-positive)]/20 text-[var(--sentiment-positive)]"
                          }`}
                        >
                          {msg.type}
                        </span>
                        {msg.replyTo && (
                          <span className="text-xs text-[var(--muted-foreground)]">
                            &rarr; {msg.replyTo}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-[var(--muted-foreground)]">{msg.timestamp}</span>
                    </div>
                    <p className="text-sm text-[var(--foreground)] mb-3">{msg.content}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex gap-4 text-xs text-[var(--muted-foreground)]">
                        <span>{"\u2665"} {msg.reactions.like}</span>
                        <span>{"\uD83D\uDCAC"} {msg.reactions.comment}</span>
                        <span>{"\uD83D\uDD04"} {msg.reactions.repost}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            msg.sentiment === "positive"
                              ? "bg-[var(--sentiment-positive)]"
                              : msg.sentiment === "negative"
                                ? "bg-[var(--sentiment-negative)]"
                                : "bg-[var(--sentiment-neutral)]"
                          }`}
                        />
                        <span className="text-xs text-[var(--muted-foreground)]">
                          Reach: {msg.reach}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Agent Intervene Modal (UI-10) */}
      <AgentInterveneModal
        isOpen={interveneOpen}
        onClose={() => setInterveneOpen(false)}
        agentId={String(agent.agentNumber)}
        agentLabel={`Agent #${agent.agentNumber}`}
      />
    </div>
  );
}
