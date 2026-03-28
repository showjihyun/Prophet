/**
 * AgentDetailPage — Agent profile, personality, activity chart, and interactions.
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import PageNav from "../components/shared/PageNav";

const MOCK_AGENT = {
  id: "A-0042",
  agentNumber: 3847,
  community: "Alpha",
  communityColor: "#3b82f6",
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
  { day: "D41", positive: 0.6, negative: -0.2 },
  { day: "D42", positive: 0.7, negative: -0.15 },
  { day: "D43", positive: 0.55, negative: -0.3 },
  { day: "D44", positive: 0.8, negative: -0.1 },
  { day: "D45", positive: 0.65, negative: -0.25 },
  { day: "D46", positive: 0.75, negative: -0.18 },
  { day: "D47", positive: 0.85, negative: -0.12 },
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

const sentimentBadge: Record<string, string> = {
  Positive: "bg-green-100 text-green-700",
  Neutral: "bg-gray-100 text-gray-600",
  Negative: "bg-red-100 text-red-700",
};

const typeBadge: Record<string, string> = {
  Share: "text-blue-600",
  Reply: "text-green-600",
  Mention: "text-orange-500",
  Influence: "text-purple-600",
};

const TABS = ["Activity", "Connections", "Messages"] as const;

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("Activity");

  const agent = { ...MOCK_AGENT, id: agentId ?? MOCK_AGENT.id };

  return (
    <div
      data-testid="agent-detail-page"
      className="min-h-screen bg-[#f8fafc] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Simulation", href: "/" },
          { label: agent.community },
          { label: `Agent #${agent.agentNumber}` },
        ]}
        actions={
          <button className="h-9 px-4 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 transition-colors">
            Intervene
          </button>
        }
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Agent Profile */}
        <aside className="w-[360px] shrink-0 border-r border-[#e5e5e5] bg-white overflow-y-auto p-6 flex flex-col gap-6">
          {/* Avatar */}
          <div className="flex flex-col items-center gap-3">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center text-white text-xl font-bold"
              style={{
                backgroundColor: agent.communityColor,
                boxShadow: `0 0 0 3px white, 0 0 0 6px ${agent.communityColor}`,
              }}
            >
              {agent.agentNumber}
            </div>
            <h2 className="text-2xl font-bold text-[#0a0a0a]">
              Agent #{agent.agentNumber}
            </h2>
            <span className="inline-flex items-center gap-1.5 text-sm bg-gray-100 px-3 py-1 rounded-full">
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
                className="bg-[#f8fafc] rounded-lg p-3 text-center"
              >
                <div className="text-xl font-bold text-[#0a0a0a]">
                  {stat.value}
                </div>
                <div className="text-xs text-[#737373]">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Personality Traits */}
          <div>
            <h3 className="text-sm font-semibold text-[#0a0a0a] mb-3">
              Personality Traits
            </h3>
            <div className="space-y-3">
              {Object.entries(agent.personality).map(([trait, value]) => (
                <div key={trait} className="flex items-center gap-2">
                  <span className="text-[13px] text-[#737373] w-24 shrink-0">
                    {trait}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-[#e2e8f0] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{ width: `${value}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-[#0a0a0a] w-10 text-right">
                    {value}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Memory Summary */}
          <div>
            <h3 className="text-sm font-semibold text-[#0a0a0a] mb-3">
              Memory Summary
            </h3>
            <div className="bg-[#f8fafc] rounded-lg p-3 text-[13px] text-[#737373] leading-relaxed border border-[#e5e5e5]">
              {agent.memorySummary}
            </div>
          </div>
        </aside>

        {/* Right Panel - Activity & Interactions */}
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {/* Tab Bar */}
          <div className="flex border-b border-[#e5e5e5]">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors relative ${
                  activeTab === tab
                    ? "text-[#0a0a0a]"
                    : "text-[#737373] hover:text-[#0a0a0a]"
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#0a0a0a]" />
                )}
              </button>
            ))}
          </div>

          {activeTab === "Activity" && (
            <>
              {/* Sentiment Over Time */}
              <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm p-4">
                <h3 className="text-sm font-semibold text-[#0a0a0a] mb-4">
                  Sentiment Over Time
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={SENTIMENT_DATA}
                    margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                  >
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis
                      domain={[-1, 1]}
                      tick={{ fontSize: 11 }}
                      tickCount={5}
                    />
                    <Tooltip
                      formatter={(value: number) => value.toFixed(2)}
                    />
                    <Bar dataKey="positive" stackId="sentiment">
                      {SENTIMENT_DATA.map((_, i) => (
                        <Cell key={i} fill="#22c55e" />
                      ))}
                    </Bar>
                    <Bar dataKey="negative" stackId="sentiment">
                      {SENTIMENT_DATA.map((_, i) => (
                        <Cell key={i} fill="#ef4444" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Recent Interactions */}
              <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm overflow-hidden">
                <div className="p-4 border-b border-[#e5e5e5]">
                  <h3 className="text-sm font-semibold text-[#0a0a0a]">
                    Recent Interactions
                  </h3>
                </div>
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-[#e5e5e5] bg-[#f8fafc]">
                      <th className="text-left px-4 py-3 font-semibold text-[#737373]">
                        Target Agent
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[#737373]">
                        Type
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[#737373]">
                        Sentiment
                      </th>
                      <th className="text-left px-4 py-3 font-semibold text-[#737373]">
                        Message Preview
                      </th>
                      <th className="text-right px-4 py-3 font-semibold text-[#737373]">
                        Time
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {MOCK_INTERACTIONS.map((interaction, i) => (
                      <tr
                        key={i}
                        className="border-b border-[#f1f5f9] hover:bg-[#f1f5f9] transition-colors"
                      >
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              navigate(`/agents/${interaction.target}`)
                            }
                            className="text-blue-600 hover:underline font-medium"
                          >
                            {interaction.target}
                          </button>
                        </td>
                        <td
                          className={`px-4 py-3 font-medium ${typeBadge[interaction.type]}`}
                        >
                          {interaction.type}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${sentimentBadge[interaction.sentiment]}`}
                          >
                            {interaction.sentiment}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[#737373] max-w-xs truncate">
                          {interaction.message}
                        </td>
                        <td className="text-right px-4 py-3 text-[#a3a3a3]">
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
            <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm p-8 flex items-center justify-center text-[#a3a3a3] min-h-[400px]">
              <div className="text-center">
                <p className="text-sm">
                  Ego network graph will render here via Cytoscape.js
                </p>
                <p className="text-xs mt-1">
                  {agent.connections} direct connections
                </p>
              </div>
            </div>
          )}

          {activeTab === "Messages" && (
            <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm p-8 flex items-center justify-center text-[#a3a3a3] min-h-[400px]">
              <div className="text-center">
                <p className="text-sm">
                  Chronological message feed will load here
                </p>
                <p className="text-xs mt-1">Infinite scroll enabled</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
