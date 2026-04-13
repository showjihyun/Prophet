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

// MOCK_CONVERSATIONS removed — the panel now derives messages from real
// step history + emergent events. When neither exists it shows an empty
// state so the user knows nothing has happened yet.

const sentimentColors: Record<string, string> = {
  Positive: "bg-[var(--sentiment-positive)]/15 text-[var(--sentiment-positive)]",
  Neutral: "bg-[var(--secondary)] text-[var(--muted-foreground)]",
  Negative: "bg-[var(--destructive)]/15 text-[var(--destructive)]",
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
  // FE-PERF-01+21: gate re-render on latestStep, read recent steps lazily
  const latestStep = useSimulationStore((s) => s.latestStep);
  const stepsLength = useSimulationStore((s) => s.steps.length);

  // Build step-derived insight messages, or fall back to emergent events, or mock data
  const conversations = useMemo<ConversationItem[]>(() => {
    // Read steps lazily — the latestStep dep covers re-render trigger
    const steps = useSimulationStore.getState().steps;
    // If steps exist, generate insight messages from step data (most recent first)
    if (steps.length > 0) {
      const insightItems: ConversationItem[] = [];

      // Walk steps in reverse to produce most-recent-first messages
      const recentSteps = steps.slice(-6).reverse();
      for (const [si, stepData] of recentSteps.entries()) {
        const prevStep = steps[stepData.step - 1] ?? null;

        // Adoption delta message
        const rate = (stepData.adoption_rate * 100).toFixed(1);
        const delta = prevStep
          ? ((stepData.adoption_rate - prevStep.adoption_rate) * 100).toFixed(1)
          : null;
        insightItems.push({
          id: `step-${stepData.step}-${si}-adopt`,
          agentId: `Step ${stepData.step}`,
          community: "System",
          communityColor: "var(--community-alpha)",
          message: delta !== null
            ? `Adoption reached ${rate}% (+${delta}% from last step)`
            : `Adoption at ${rate}%`,
          sentiment: stepData.adoption_rate > 0.3 ? "Positive" : stepData.adoption_rate > 0.1 ? "Neutral" : "Negative",
          time: `Step ${stepData.step}`,
        });

        // Sentiment message
        const sentimentPct = (stepData.mean_sentiment * 100).toFixed(0);
        const sentimentDir = stepData.mean_sentiment >= 0 ? "positive" : "negative";
        insightItems.push({
          id: `step-${stepData.step}-${si}-sentiment`,
          agentId: `Step ${stepData.step}`,
          community: "Sentiment",
          communityColor: stepData.mean_sentiment >= 0 ? "var(--sentiment-positive)" : "var(--destructive)",
          message: `Sentiment shifted to ${sentimentDir}: ${sentimentPct}%`,
          sentiment: stepData.mean_sentiment >= 0.2 ? "Positive" : stepData.mean_sentiment <= -0.2 ? "Negative" : "Neutral",
          time: `Step ${stepData.step}`,
        });

        // Dominant action from action_distribution
        const actionDist = stepData.action_distribution;
        const topAction = Object.entries(actionDist).sort((a, b) => b[1] - a[1])[0];
        if (topAction) {
          insightItems.push({
            id: `step-${stepData.step}-${si}-action`,
            agentId: `Step ${stepData.step}`,
            community: "Actions",
            communityColor: "var(--community-delta)",
            message: `Top action: ${topAction[0]} (${topAction[1]} agents)`,
            sentiment: "Neutral",
            time: `Step ${stepData.step}`,
          });
        }

        // Emergent events from this step.
        // Key includes the event-loop index `ei` so the row stays unique
        // even if a step emits two events of the same type (e.g. viral
        // cascades in two communities at once). The 2026-04 root fix at
        // backend `/steps` (event_type was emitted as `type`, hiding the
        // real names) means `event.event_type` should always be defined
        // for fresh runs — `?? "unknown"` only triggers on legacy data.
        for (const [ei, event] of stepData.emergent_events.entries()) {
          insightItems.push({
            id: `step-${stepData.step}-${si}-event-${ei}-${event.event_type ?? "unknown"}`,
            agentId: event.community_id ?? "System",
            community: event.community_id ?? "Alert",
            communityColor: EVENT_COMMUNITY_COLORS[event.community_id?.toLowerCase() ?? ""] ?? "var(--destructive)",
            message: `Alert: ${(event.event_type ?? "unknown").replace(/_/g, " ")} detected! ${event.description ?? ""}`,
            sentiment: severityToSentiment(event.severity),
            time: `Step ${event.step}`,
          });
        }
      }

      return insightItems.slice(0, 12);
    }

    // Fall back to emergent events as conversation items
    if (emergentEvents.length > 0) {
      return emergentEvents.slice(-6).reverse().map((event, i) => ({
        id: `event-${i}`,
        agentId: event.community_id ?? "System",
        community: event.community_id ?? "System",
        communityColor: EVENT_COMMUNITY_COLORS[event.community_id?.toLowerCase() ?? ""] ?? "var(--community-bridge)",
        message: event.description,
        sentiment: severityToSentiment(event.severity),
        time: `Step ${event.step}`,
      }));
    }

    // Real-data-only: empty list when there are no steps and no events.
    return [];
    // FE-PERF-01: latestStep+stepsLength are intentional re-render gates for the lazy steps read
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, stepsLength, emergentEvents]);

  // Build expert analysis from latest step data — empty when no step yet.
  const expertAnalysis = useMemo(() => {
    if (!latestStep) {
      return "No step data yet. Start the simulation to see live expert analysis.";
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
      // `overflow-hidden` + `min-h-0` guarantee that nothing inside this
      // panel can push past the fixed Zone-3 height (no vertical scroll).
      className="flex border-t border-[var(--border)] bg-[var(--card)] overflow-hidden min-h-0"
      style={{ height: "calc(var(--bottom-area-height) - var(--timeline-height))" }}
    >
      {/* Expert Agent Analysis */}
      <div data-testid="expert-agent-analysis" className="w-[360px] shrink-0 border-r border-[var(--border)] p-3 flex flex-col gap-2 min-h-0">
        <div className="flex items-center gap-2 shrink-0">
          <Brain className="w-4 h-4 text-[var(--community-delta)]" />
          <span className="text-xs font-semibold text-[var(--foreground)]">
            Expert Agent Analysis
          </span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${latestStep ? "bg-[var(--sentiment-positive)]/15 text-[var(--sentiment-positive)]" : "bg-[var(--sentiment-warning)]/15 text-[var(--sentiment-warning)] animate-pulse-dot"}`}>
            {latestStep ? `Step ${latestStep.step}` : "Analyzing"}
          </span>
        </div>
        <div className="flex-1 min-h-0 text-[12px] leading-relaxed text-[var(--muted-foreground)] bg-[var(--secondary)] rounded-md p-2.5 overflow-y-auto">
          {expertAnalysis}
        </div>
      </div>

      {/* Live Conversation Feed — horizontally scrolling compact cards.
          No vertical scroll: the card's intrinsic height is smaller than
          the container's fixed height (`bottom-area - timeline`), so the
          `overflow-y-hidden` below is a safety belt rather than a crutch. */}
      <div className="flex-1 p-3 flex flex-col gap-2 min-h-0 overflow-hidden">
        <div className="flex items-center gap-2 shrink-0">
          <MessageCircle className="w-4 h-4 text-[var(--muted-foreground)]" />
          <span className="text-xs font-semibold text-[var(--foreground)]">
            Live Conversation Feed
          </span>
        </div>
        <div className="flex-1 min-h-0 flex gap-2 overflow-x-auto overflow-y-hidden items-stretch">
          {conversations.length === 0 && (
            <div className="text-[11px] text-[var(--muted-foreground)] px-2 self-center">
              No conversations yet — run the simulation to see live messages.
            </div>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="shrink-0 w-[220px] rounded-lg border border-[var(--border)] bg-[var(--card)] px-2.5 py-1.5 flex flex-col gap-1 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold text-white shrink-0"
                  style={{ backgroundColor: conv.communityColor }}
                >
                  {conv.agentId.charAt(0)}
                </span>
                <span className="text-[11px] font-medium text-[var(--foreground)] truncate">
                  {conv.agentId}
                </span>
                <span
                  className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ml-auto shrink-0 ${sentimentColors[conv.sentiment]}`}
                >
                  {conv.sentiment}
                </span>
              </div>
              <p className="text-[11px] text-[var(--muted-foreground)] leading-snug line-clamp-1">
                {conv.message}
              </p>
              <span className="text-[9px] text-[var(--muted-foreground)] truncate">
                {conv.time}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
