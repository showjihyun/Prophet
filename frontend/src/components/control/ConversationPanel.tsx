/**
 * ConversationPanel — Bottom panel (Zone 3 lower).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-3-conversations-expert-agent
 *
 * Left: Expert Agent Analysis with brain icon + analysis text
 * Right: Live Conversation Feed with message cards
 */
import { useMemo } from "react";
import { Brain, MessageCircle } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";

interface ConversationItem {
  id: string;
  agentId: string;
  community: string;
  communityColor: string;
  message: string;
  sentiment: "Positive" | "Neutral" | "Negative";
  time: string;
}

const MOCK_CONVERSATIONS: ConversationItem[] = [
  {
    id: "conv-1",
    agentId: "A-0042",
    community: "Alpha",
    communityColor: "var(--community-alpha)",
    message:
      "This campaign is gaining traction in my network. 3 of my closest connections have already adopted it.",
    sentiment: "Positive",
    time: "2m ago",
  },
  {
    id: "conv-2",
    agentId: "BR-0012",
    community: "Bridge",
    communityColor: "var(--community-bridge)",
    message:
      "Interesting cross-community pattern emerging. Alpha and Beta are converging on this topic.",
    sentiment: "Neutral",
    time: "5m ago",
  },
  {
    id: "conv-3",
    agentId: "G-0055",
    community: "Gamma",
    communityColor: "var(--community-gamma)",
    message:
      "I remain skeptical about the claims. Need more evidence before sharing further.",
    sentiment: "Negative",
    time: "8m ago",
  },
];

const sentimentColors: Record<string, string> = {
  Positive: "bg-green-100 text-green-700",
  Neutral: "bg-gray-100 text-gray-600",
  Negative: "bg-red-100 text-red-700",
};

const EVENT_COMMUNITY_COLORS: Record<string, string> = {
  alpha: "var(--community-alpha)",
  beta: "var(--community-beta)",
  gamma: "var(--community-gamma)",
  delta: "var(--community-delta)",
  bridge: "var(--community-bridge)",
};

function severityToSentiment(severity: number): "Positive" | "Neutral" | "Negative" {
  if (severity < 0.3) return "Positive";
  if (severity < 0.7) return "Neutral";
  return "Negative";
}

export default function ConversationPanel() {
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);
  const steps = useSimulationStore((s) => s.steps);
  const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;

  // Convert emergent events to conversation items, or use mock data
  const conversations = useMemo<ConversationItem[]>(() => {
    if (emergentEvents.length === 0) return MOCK_CONVERSATIONS;

    return emergentEvents.slice(-6).reverse().map((event, i) => ({
      id: `event-${i}`,
      agentId: event.community_id ?? "System",
      community: event.community_id ?? "System",
      communityColor: EVENT_COMMUNITY_COLORS[event.community_id?.toLowerCase() ?? ""] ?? "var(--community-bridge)",
      message: event.description,
      sentiment: severityToSentiment(event.severity),
      time: `Step ${event.step}`,
    }));
  }, [emergentEvents]);

  // Build expert analysis from latest step data or use mock text
  const expertAnalysis = useMemo(() => {
    if (!latestStep) {
      return "Community Alpha shows accelerating adoption with 62% positive sentiment. Bridge agents (BR-0012, BR-0034) are critical for cross-community propagation. Cascade #47 has reached depth 12, indicating strong viral potential. Recommend increasing stimulus in Gamma community where skepticism remains at 25%.";
    }

    const adoption = latestStep.total_adoption;
    const sentiment = (latestStep.mean_sentiment * 100).toFixed(0);
    const rate = (latestStep.adoption_rate * 100).toFixed(1);
    const events = latestStep.emergent_events.length;
    return `Step ${latestStep.step}: ${adoption} total adoptions (${rate}% rate). Mean sentiment: ${sentiment}%. ${events} emergent event(s) detected this step. Diffusion rate: ${(latestStep.diffusion_rate * 100).toFixed(1)}%. Step completed in ${latestStep.step_duration_ms}ms with ${latestStep.llm_calls_this_step} LLM calls.`;
  }, [latestStep]);
  return (
    <div
      data-testid="conversation-panel"
      className="flex border-t border-[var(--border)] bg-white"
      style={{ height: "calc(var(--bottom-area-height) - var(--timeline-height))" }}
    >
      {/* Expert Agent Analysis */}
      <div className="w-[360px] shrink-0 border-r border-[var(--border)] p-3 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-[var(--community-delta)]" />
          <span className="text-xs font-semibold text-[var(--foreground)]">
            Expert Agent Analysis
          </span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${latestStep ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700 animate-pulse-dot"}`}>
            {latestStep ? `Step ${latestStep.step}` : "Analyzing"}
          </span>
        </div>
        <div className="flex-1 text-[12px] leading-relaxed text-[var(--muted-foreground)] bg-[var(--secondary)] rounded-md p-2.5 overflow-y-auto">
          {expertAnalysis}
        </div>
      </div>

      {/* Live Conversation Feed */}
      <div className="flex-1 p-3 flex flex-col gap-2 overflow-hidden">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-[var(--muted-foreground)]" />
          <span className="text-xs font-semibold text-[var(--foreground)]">
            Live Conversation Feed
          </span>
        </div>
        <div className="flex-1 flex gap-2 overflow-x-auto">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="shrink-0 w-[240px] rounded-lg border border-[var(--border)] bg-white p-2.5 flex flex-col gap-1.5 hover:shadow-sm transition-shadow cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white shrink-0"
                  style={{ backgroundColor: conv.communityColor }}
                >
                  {conv.agentId.charAt(0)}
                </span>
                <span className="text-[11px] font-medium text-[var(--foreground)]">
                  {conv.agentId}
                </span>
                <span
                  className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ml-auto ${sentimentColors[conv.sentiment]}`}
                >
                  {conv.sentiment}
                </span>
              </div>
              <p className="text-[11px] text-[var(--muted-foreground)] leading-snug line-clamp-2">
                {conv.message}
              </p>
              <span className="text-[9px] text-[var(--muted-foreground)]">
                {conv.time}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
