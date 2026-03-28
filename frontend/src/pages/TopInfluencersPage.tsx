/**
 * TopInfluencersPage — Ranked influencer table with distribution sidebar.
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
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

const MOCK_INFLUENCERS: Influencer[] = [
  { rank: 1, agentId: "A-0042", community: "Alpha", communityColor: "#3b82f6", influenceScore: 98.2, sentiment: "Positive", chains: 24, connections: 247, status: "Active" },
  { rank: 2, agentId: "BR-0012", community: "Bridge", communityColor: "#ef4444", influenceScore: 96.5, sentiment: "Neutral", chains: 31, connections: 189, status: "Active" },
  { rank: 3, agentId: "B-0091", community: "Beta", communityColor: "#22c55e", influenceScore: 94.7, sentiment: "Positive", chains: 19, connections: 203, status: "Active" },
  { rank: 4, agentId: "D-0067", community: "Delta", communityColor: "#a855f7", influenceScore: 92.1, sentiment: "Positive", chains: 17, connections: 178, status: "Active" },
  { rank: 5, agentId: "A-0187", community: "Alpha", communityColor: "#3b82f6", influenceScore: 91.5, sentiment: "Neutral", chains: 15, connections: 156, status: "Active" },
  { rank: 6, agentId: "BR-0034", community: "Bridge", communityColor: "#ef4444", influenceScore: 90.2, sentiment: "Negative", chains: 22, connections: 134, status: "Idle" },
  { rank: 7, agentId: "B-0203", community: "Beta", communityColor: "#22c55e", influenceScore: 88.3, sentiment: "Positive", chains: 12, connections: 145, status: "Active" },
  { rank: 8, agentId: "D-0145", community: "Delta", communityColor: "#a855f7", influenceScore: 86.8, sentiment: "Neutral", chains: 14, connections: 121, status: "Active" },
  { rank: 9, agentId: "G-0055", community: "Gamma", communityColor: "#f97316", influenceScore: 85.9, sentiment: "Positive", chains: 11, connections: 132, status: "Idle" },
  { rank: 10, agentId: "A-0334", community: "Alpha", communityColor: "#3b82f6", influenceScore: 87.1, sentiment: "Neutral", chains: 13, connections: 118, status: "Active" },
];

const DISTRIBUTION_DATA = [
  { name: "Alpha", value: 120, fill: "#3b82f6" },
  { name: "Beta", value: 85, fill: "#22c55e" },
  { name: "Gamma", value: 52, fill: "#f97316" },
  { name: "Delta", value: 65, fill: "#a855f7" },
  { name: "Bridge", value: 20, fill: "#ef4444" },
];

const sentimentBadge: Record<string, string> = {
  Positive: "bg-green-100 text-green-700",
  Neutral: "bg-gray-100 text-gray-600",
  Negative: "bg-red-100 text-red-700",
};

const statusBadge: Record<string, string> = {
  Active: "bg-green-100 text-green-700",
  Idle: "bg-gray-100 text-gray-500",
};

export default function TopInfluencersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const filtered = MOCK_INFLUENCERS.filter(
    (i) =>
      i.agentId.toLowerCase().includes(search.toLowerCase()) ||
      i.community.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div
      data-testid="top-influencers-page"
      className="min-h-screen bg-[#f8fafc] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Top Influencers" },
        ]}
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto">
        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Influencers Tracked" value="342" icon={<CrownIcon />} />
          <StatCard label="Avg Influence Score" value="74.3" icon={<BarChartIcon />} />
          <StatCard
            label="Top Community"
            value="Alpha"
            icon={
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
              </span>
            }
          />
          <StatCard label="Active Cascades" value="89" icon={<ZapIcon />} />
        </div>

        {/* Content area: table + sidebar */}
        <div className="flex gap-6">
          {/* Main table area */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Search + Filter */}
            <div className="flex gap-3">
              <div className="relative flex-1">
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a3a3a3]"
                  width="16"
                  height="16"
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
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-10 pl-9 pr-4 text-sm border border-[#e5e5e5] rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-[#a3a3a3]"
                />
              </div>
              <button className="h-10 px-4 text-sm border border-[#e5e5e5] rounded-md bg-white hover:bg-gray-50 flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
                Filter
              </button>
            </div>

            {/* Data Table */}
            <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm overflow-hidden">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-[#e5e5e5] bg-[#f8fafc]">
                    <th className="text-right px-3 py-3 font-semibold text-[#737373] w-12">#</th>
                    <th className="text-left px-3 py-3 font-semibold text-[#737373]">Agent ID</th>
                    <th className="text-left px-3 py-3 font-semibold text-[#737373]">Community</th>
                    <th className="text-left px-3 py-3 font-semibold text-[#737373] w-48">Influence Score</th>
                    <th className="text-left px-3 py-3 font-semibold text-[#737373]">Sentiment</th>
                    <th className="text-right px-3 py-3 font-semibold text-[#737373]">Chains</th>
                    <th className="text-right px-3 py-3 font-semibold text-[#737373]">Connections</th>
                    <th className="text-left px-3 py-3 font-semibold text-[#737373]">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((inf) => (
                    <tr
                      key={inf.agentId}
                      className="border-b border-[#f1f5f9] hover:bg-[#f1f5f9] transition-colors cursor-pointer"
                      onClick={() => navigate(`/agents/${inf.agentId}`)}
                    >
                      <td className="text-right px-3 py-3 font-semibold text-[#737373]">
                        {inf.rank}
                      </td>
                      <td className="px-3 py-3 font-medium text-blue-600 hover:underline">
                        {inf.agentId}
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: inf.communityColor }}
                          />
                          {inf.community}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 rounded-full bg-[#e2e8f0] overflow-hidden">
                            <div
                              className="h-full rounded-full bg-blue-500"
                              style={{ width: `${inf.influenceScore}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium w-10 text-right">
                            {inf.influenceScore}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${sentimentBadge[inf.sentiment]}`}
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
                          className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${statusBadge[inf.status]}`}
                        >
                          {inf.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="w-[280px] shrink-0">
            <div className="bg-white rounded-lg border border-[#e5e5e5] shadow-sm p-4">
              <h3 className="text-sm font-semibold text-[#0a0a0a] mb-4">
                Influence Distribution
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={DISTRIBUTION_DATA}
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
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {DISTRIBUTION_DATA.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
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

function ZapIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}
