/**
 * ConversationThreadPage — Agent conversation thread with reactions (UI-15).
 * @spec docs/spec/ui/UI_15_CONVERSATION_THREAD.md
 */
import { useMemo, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import PageNav from "../components/shared/PageNav";
import { useSimulationStore } from "../store/simulationStore";
import { apiClient, type ThreadDetail } from "../api/client";

/* ------------------------------------------------------------------ */
/* Mock Data                                                           */
/* ------------------------------------------------------------------ */

interface ThreadMsg {
  message_id: string;
  agent_id: string;
  community_color: string;
  stance: "Progressive" | "Conservative" | "Neutral";
  relative_time: string;
  content: string;
  reactions: { agree: number; disagree: number; nuanced: number };
  is_reply: boolean;
  reply_to_id: string | null;
}

const MOCK_THREAD = {
  thread_id: "t1",
  topic: "Debate on progressive taxation reform impact",
  category_tag: "Election Reform",
  participant_count: 8,
  timespan: "2h 15m",
  avg_sentiment: 0.2,
  message_count: 24,
};

const MOCK_MESSAGES: ThreadMsg[] = [
  {
    message_id: "m1",
    agent_id: "Agent-A042",
    community_color: "var(--community-alpha)",
    stance: "Progressive",
    relative_time: "2h ago",
    content:
      "The progressive taxation reform would significantly reduce income inequality in our society. Studies from Nordic countries show that higher marginal tax rates on top earners, when paired with robust social programs, lead to better outcomes across all economic strata. We should be looking at comprehensive reform rather than incremental adjustments.",
    reactions: { agree: 12, disagree: 3, nuanced: 5 },
    is_reply: false,
    reply_to_id: null,
  },
  {
    message_id: "m2",
    agent_id: "Agent-B091",
    community_color: "var(--community-beta)",
    stance: "Conservative",
    relative_time: "1h 50m ago",
    content:
      "While I understand the intent behind progressive taxation, the economic impact on small businesses and entrepreneurship cannot be ignored. Higher tax rates discourage investment and innovation. We need to find a balance that supports growth while ensuring fairness. The Laffer curve suggests there's an optimal point beyond which higher rates actually reduce revenue.",
    reactions: { agree: 8, disagree: 7, nuanced: 3 },
    is_reply: false,
    reply_to_id: null,
  },
  {
    message_id: "m3",
    agent_id: "Agent-A042",
    community_color: "var(--community-alpha)",
    stance: "Progressive",
    relative_time: "1h 45m ago",
    content:
      "That's a valid concern, but consider the data from countries that have implemented these reforms. Small business growth rates in Scandinavian countries remain competitive with lower-tax jurisdictions. The key is in how the revenue is reinvested — education, infrastructure, and healthcare create a more productive workforce that benefits everyone.",
    reactions: { agree: 6, disagree: 2, nuanced: 4 },
    is_reply: true,
    reply_to_id: "m2",
  },
  {
    message_id: "m4",
    agent_id: "Agent-G055",
    community_color: "var(--community-gamma)",
    stance: "Neutral",
    relative_time: "1h 30m ago",
    content:
      "Both sides make valid points. The key question is whether we can design a tax system that captures the benefits of progressive taxation while minimizing disincentives for productive economic activity. Perhaps a consumption-based approach combined with targeted credits could bridge the gap between these perspectives.",
    reactions: { agree: 15, disagree: 1, nuanced: 8 },
    is_reply: false,
    reply_to_id: null,
  },
  {
    message_id: "m5",
    agent_id: "Agent-D067",
    community_color: "var(--community-delta)",
    stance: "Conservative",
    relative_time: "1h 15m ago",
    content:
      "The fundamental issue is government efficiency. Before we raise taxes, we should ensure existing revenue is being spent wisely. There's significant waste in current programs that could be redirected to social priorities without any tax increases. Let's focus on accountability first.",
    reactions: { agree: 9, disagree: 5, nuanced: 6 },
    is_reply: false,
    reply_to_id: null,
  },
  {
    message_id: "m6",
    agent_id: "Agent-BR012",
    community_color: "var(--community-bridge)",
    stance: "Neutral",
    relative_time: "58m ago",
    content:
      "I think we're approaching this too ideologically. Economic policy should be evidence-based. We have data from dozens of countries with different tax regimes. Rather than debating principles, let's look at what actually works for societies similar to ours and adapt accordingly.",
    reactions: { agree: 11, disagree: 2, nuanced: 7 },
    is_reply: false,
    reply_to_id: null,
  },
];

/* ------------------------------------------------------------------ */
/* Stance badge styling                                                */
/* ------------------------------------------------------------------ */

const STANCE_STYLES: Record<string, string> = {
  Progressive: "bg-[var(--community-alpha)]/20 text-[var(--community-alpha)]",
  Conservative: "bg-[var(--destructive)]/20 text-[var(--destructive)]",
  Neutral: "bg-[var(--muted-foreground)]/20 text-[var(--muted-foreground)]",
};

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

const COMMUNITY_COLORS_ARRAY = [
  "var(--community-alpha)",
  "var(--community-beta)",
  "var(--community-gamma)",
  "var(--community-delta)",
  "var(--community-bridge)",
];

export default function ConversationThreadPage() {
  const { communityId, threadId: _threadId } = useParams<{ communityId: string; threadId: string }>();
  const navigate = useNavigate();
  const simulation = useSimulationStore((st) => st.simulation);
  const steps = useSimulationStore((st) => st.steps);
  const emergentEvents = useSimulationStore((st) => st.emergentEvents);

  // API-fetched thread detail
  const [apiThread, setApiThread] = useState<ThreadDetail | null>(null);
  const [apiLoading, setApiLoading] = useState(false);

  useEffect(() => {
    if (!simulation?.simulation_id || !communityId || !_threadId) return;
    setApiLoading(true);
    apiClient.communityThreads
      .get(simulation.simulation_id, communityId, _threadId)
      .then((data) => setApiThread(data))
      .catch(() => setApiThread(null))
      .finally(() => setApiLoading(false));
  }, [simulation?.simulation_id, communityId, _threadId]);

  // Derive thread header from store data (fallback when no API data)
  const derivedThread = useMemo(() => {
    if (steps.length === 0) return null;
    const latest = steps[steps.length - 1];
    const cm = communityId ? latest.community_metrics?.[communityId] : null;
    const participantIds = Object.keys(latest.community_metrics ?? {});
    return {
      thread_id: _threadId ?? "auto",
      topic: cm
        ? `Step ${latest.step}: ${cm.dominant_action} dominant — ${Math.round(cm.adoption_rate * 100)}% adoption`
        : `Simulation at Step ${latest.step}`,
      category_tag: cm?.dominant_action ?? "simulation",
      participant_count: participantIds.length,
      timespan: `${latest.step_duration_ms ? (latest.step_duration_ms / 1000).toFixed(1) : "0"} s/step`,
      avg_sentiment: latest.mean_sentiment,
      message_count: steps.length,
    };
  }, [steps, communityId, _threadId]);

  // Derive messages from step history — used as fallback
  const derivedMessages = useMemo<ThreadMsg[]>(() => {
    if (steps.length === 0) return [];
    const communityKeys = steps.length > 0 ? Object.keys(steps[0].community_metrics ?? {}) : [];
    return steps.map((step, idx): ThreadMsg => {
      const topAction = Object.entries(step.action_distribution ?? {})
        .sort((a, b) => b[1] - a[1])[0];
      const actionName = topAction?.[0] ?? "observe";
      const adoptPct = Math.round(step.adoption_rate * 100);
      const sentiment = step.mean_sentiment;
      const communityColorIdx = idx % communityKeys.length;
      const stance: ThreadMsg["stance"] =
        sentiment > 0.1 ? "Progressive" : sentiment < -0.1 ? "Conservative" : "Neutral";

      // Check if any emergent event occurred at this step
      const event = emergentEvents.find((e) => e.step === step.step);

      return {
        message_id: `step-${step.step}`,
        agent_id: `Step-${step.step}`,
        community_color: COMMUNITY_COLORS_ARRAY[communityColorIdx] ?? "var(--community-alpha)",
        stance,
        relative_time: `Step ${step.step}`,
        content: event
          ? `[${event.event_type.replace(/_/g, " ").toUpperCase()}] ${event.description} — ${step.llm_calls_this_step} LLM calls, ${adoptPct}% adoption rate.`
          : `${step.llm_calls_this_step} LLM calls this step. Dominant action: ${actionName} (${adoptPct}% adoption). Sentiment: ${sentiment > 0 ? "+" : ""}${sentiment.toFixed(2)}.`,
        reactions: {
          agree: Math.round(step.adoption_rate * 20),
          disagree: Math.round((1 - step.adoption_rate) * 10),
          nuanced: step.llm_calls_this_step,
        },
        is_reply: idx > 0,
        reply_to_id: idx > 0 ? `step-${steps[idx - 1].step}` : null,
      };
    });
  }, [steps, emergentEvents]);

  // Resolve display data: API → derived from store → mock
  const t = apiThread
    ? {
        thread_id: apiThread.thread_id,
        topic: apiThread.topic,
        category_tag: communityId ?? "community",
        participant_count: apiThread.participant_count,
        timespan: `${apiThread.message_count} messages`,
        avg_sentiment: apiThread.avg_sentiment,
        message_count: apiThread.message_count,
      }
    : derivedThread ?? MOCK_THREAD;

  const messages: ThreadMsg[] = apiThread
    ? apiThread.messages.map((m) => {
        const colorIdx = m.agent_id.charCodeAt(m.agent_id.length - 1) % COMMUNITY_COLORS_ARRAY.length;
        return {
          message_id: m.message_id,
          agent_id: m.agent_id,
          community_color: COMMUNITY_COLORS_ARRAY[colorIdx] ?? "var(--community-alpha)",
          stance: m.stance as ThreadMsg["stance"],
          relative_time: "",
          content: m.content,
          reactions: m.reactions,
          is_reply: m.is_reply,
          reply_to_id: m.reply_to_id,
        };
      })
    : derivedMessages.length > 0
    ? derivedMessages
    : MOCK_MESSAGES;

  const sentColor = t.avg_sentiment > 0.1 ? "text-[var(--sentiment-positive)]" : t.avg_sentiment < -0.1 ? "text-[var(--destructive)]" : "text-[var(--muted-foreground)]";

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[var(--background)]">
      {/* Nav */}
      <PageNav
        breadcrumbs={[
          { label: "Korea Election 2026", href: "/projects/p1" },
          { label: "Alpha", href: `/opinions/${communityId ?? "alpha"}` },
          { label: "Conversation" },
        ]}
        actions={
          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--community-delta)]/20 text-[var(--community-delta)] border border-[var(--community-delta)]/30">
            Level 3
          </span>
        }
      />

      {/* Header */}
      <div className="px-8 py-5 border-b border-[var(--border)]">
        <div className="flex items-start justify-between">
          <div>
            <h1
              className="text-xl font-semibold text-[var(--foreground)] mb-2"
              style={{ fontFamily: "'Instrument Serif', serif" }}
            >
              {t.topic}
            </h1>
            <div className="flex items-center gap-3 text-sm">
              <span className="px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--foreground)] text-xs">
                {t.category_tag}
              </span>
              <span className="text-[var(--muted-foreground)] flex items-center gap-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                Participants {t.participant_count}
              </span>
              <span className="text-[var(--muted-foreground)] flex items-center gap-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12,6 12,12 16,14" />
                </svg>
                {t.timespan}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <span className="text-[var(--muted-foreground)]">
              Participants <strong className="text-[var(--foreground)]">{t.participant_count}</strong>
            </span>
            <span className={`px-2 py-0.5 rounded-full bg-[var(--secondary)] text-xs ${sentColor}`}>
              Avg Sentiment {t.avg_sentiment > 0 ? "+" : ""}{t.avg_sentiment.toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      {/* Thread body */}
      <div className="flex-1 overflow-y-auto">
        {apiLoading && (
          <div className="flex items-center justify-center py-12 text-sm text-[var(--muted-foreground)]">
            Loading thread…
          </div>
        )}
        <div className="max-w-4xl mx-auto">
          {!apiLoading && messages.map((msg, idx) => (
            <div
              key={msg.message_id}
              data-testid={msg.is_reply ? "thread-reply" : "thread-message"}
              className={`border-b border-[var(--border)] hover:bg-[var(--card)] transition-colors ${
                msg.is_reply ? "pl-12" : ""
              }`}
              style={{ padding: msg.is_reply ? "16px 24px 16px 48px" : "20px 24px" }}
            >
              {/* Author row */}
              <div className="flex items-center gap-3 mb-3">
                {/* Avatar */}
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-medium text-white shrink-0"
                  style={{ backgroundColor: msg.community_color }}
                >
                  {msg.agent_id.slice(-3)}
                </div>

                <span className="font-medium text-sm text-[var(--foreground)]">
                  {msg.agent_id}
                </span>

                <span className={`text-xs px-2 py-0.5 rounded-full ${STANCE_STYLES[msg.stance]}`}>
                  {msg.stance}
                </span>

                <span className="text-xs text-[var(--muted-foreground)] ml-auto">
                  {msg.relative_time}
                </span>
              </div>

              {/* Content */}
              <p
                className="text-sm text-[var(--foreground)] leading-relaxed mb-3 opacity-90"
                style={{ fontFamily: "'Geist', sans-serif" }}
              >
                {msg.content}
              </p>

              {/* Reactions */}
              <div className="flex items-center gap-4">
                <button className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--sentiment-positive)] transition-colors">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
                    <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                  </svg>
                  Agree {msg.reactions.agree}
                </button>
                <button className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--destructive)] transition-colors">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 15V19a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
                    <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
                  </svg>
                  Disagree {msg.reactions.disagree}
                </button>
                <button className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--sentiment-warning)] transition-colors">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M8 15h8" />
                    <path d="M9 9h.01" />
                    <path d="M15 9h.01" />
                  </svg>
                  Nuanced {msg.reactions.nuanced}
                </button>
              </div>

              {/* Reply indicator */}
              {msg.is_reply && idx > 0 && (
                <div className="mt-2 text-xs text-[var(--muted-foreground)] opacity-60">
                  Replying to {messages.find((m) => m.message_id === msg.reply_to_id)?.agent_id ?? "..."}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
