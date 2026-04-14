/**
 * EliteLLMNarrativePanel — EliteLLM-synthesized community narrative.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
 *
 * Renders a "Synthesize with EliteLLM" button. On click it calls the
 * backend, which either returns a cached snapshot (idempotent on
 * (simulation_id, community_id, current_step)) or pays one Tier-3 LLM
 * call to build a fresh narrative.
 *
 * The panel is intentionally additive — existing community insight UI
 * (opinion clusters, conversations) is untouched. This is the "why did
 * the community behave this way" explainer that sits above them.
 */
import {
  useCommunityOpinionSynthesis,
  useCommunityOpinionQuery,
} from "@/api/queries";
import type { CommunityOpinion } from "@/types/api";

interface Props {
  simulationId: string | null;
  communityId: string | null;
}

const SENTIMENT_LABEL: Record<string, string> = {
  rising: "Rising — momentum building",
  stable: "Stable — no strong trend",
  polarising: "Polarising — factions hardening",
  collapsing: "Collapsing — adoption unwinding",
};

const SENTIMENT_COLOR: Record<string, string> = {
  rising: "var(--sentiment-positive)",
  stable: "var(--muted-foreground)",
  polarising: "var(--sentiment-neutral)",
  collapsing: "var(--destructive)",
};

export default function EliteLLMNarrativePanel({
  simulationId,
  communityId,
}: Props) {
  const cachedQuery = useCommunityOpinionQuery(simulationId, communityId);
  const mutation = useCommunityOpinionSynthesis(simulationId);
  // Prefer fresh mutation result; fall back to TanStack cache (survives
  // page navigation so users don't re-click after a round-trip).
  const opinion = (mutation.data ?? cachedQuery.data ?? null) as CommunityOpinion | null;

  const canRun = Boolean(simulationId && communityId) && !mutation.isPending;

  const handleClick = () => {
    if (!communityId) return;
    mutation.mutate(communityId);
  };

  return (
    <div
      data-testid="elite-llm-narrative-panel"
      className="mx-8 mt-4 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-base font-semibold text-[var(--foreground)]">
            EliteLLM Opinion Narrative
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
            Synthesised from raw simulation metrics by a Tier-3 research analyst.
          </p>
        </div>
        <button
          type="button"
          disabled={!canRun}
          onClick={handleClick}
          className="text-xs px-3 py-1.5 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending
            ? "Synthesising…"
            : opinion
              ? "Refresh"
              : "Synthesise with EliteLLM"}
        </button>
      </div>

      {mutation.isError && (
        <div className="text-xs text-[var(--destructive)] mb-2">
          Synthesis failed:{" "}
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Unknown error"}
        </div>
      )}

      {!opinion && !mutation.isPending && !mutation.isError && (
        <p className="text-sm text-[var(--muted-foreground)]">
          Click <span className="font-medium">Synthesise with EliteLLM</span> to
          generate a structured narrative explaining this community's recent
          behaviour. Results are cached per simulation step — running it twice
          at the same step is free.
        </p>
      )}

      {opinion && <NarrativeBody opinion={opinion} />}
    </div>
  );
}

function NarrativeBody({ opinion }: { opinion: CommunityOpinion }) {
  const trendLabel =
    SENTIMENT_LABEL[opinion.sentiment_trend] ?? opinion.sentiment_trend;
  const trendColor =
    SENTIMENT_COLOR[opinion.sentiment_trend] ?? "var(--muted-foreground)";

  return (
    <div className="flex flex-col gap-4">
      {opinion.is_fallback_stub && (
        <div className="text-xs px-2 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-600">
          Fallback stub — every configured LLM adapter failed, so this is a
          rule-engine placeholder rather than a real LLM completion.
        </div>
      )}

      <p className="text-sm text-[var(--foreground)] leading-relaxed">
        {opinion.summary}
      </p>

      <div className="flex items-center gap-2 text-xs">
        <span className="text-[var(--muted-foreground)]">Trend:</span>
        <span
          className="font-medium px-2 py-0.5 rounded"
          style={{ color: trendColor, borderColor: `${trendColor}33` }}
        >
          {trendLabel}
        </span>
        <span className="text-[var(--muted-foreground)]">·</span>
        <span className="text-[var(--muted-foreground)]">
          {opinion.source_agent_count} agents across {opinion.source_step_count}{" "}
          steps
        </span>
        <span className="text-[var(--muted-foreground)]">·</span>
        <span className="text-[var(--muted-foreground)]">
          {opinion.llm_provider}/{opinion.llm_model}
        </span>
      </div>

      {opinion.themes.length > 0 && (
        <Section title="Themes">
          <ul className="flex flex-col gap-1">
            {opinion.themes.map((t, idx) => (
              <li
                key={`${t.theme}-${idx}`}
                className="flex items-baseline gap-2 text-sm"
              >
                <span
                  className="inline-block w-12 text-right text-xs tabular-nums text-[var(--muted-foreground)]"
                  aria-label="weight"
                >
                  {(t.weight * 100).toFixed(0)}%
                </span>
                <span className="text-[var(--foreground)]">{t.theme}</span>
                <span className="text-xs text-[var(--muted-foreground)]">
                  (step {t.evidence_step})
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {opinion.divisions.length > 0 && (
        <Section title="Divisions">
          <ul className="flex flex-col gap-1">
            {opinion.divisions.map((d, idx) => (
              <li key={`${d.faction}-${idx}`} className="text-sm">
                <span className="font-medium text-[var(--foreground)]">
                  {d.faction}
                </span>{" "}
                <span className="text-[var(--muted-foreground)]">
                  ({(d.share * 100).toFixed(0)}%)
                </span>
                {d.concerns.length > 0 && (
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {" "}
                    — {d.concerns.join(", ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {opinion.dominant_emotions.length > 0 && (
        <Section title="Dominant Emotions">
          <div className="flex flex-wrap gap-1.5">
            {opinion.dominant_emotions.map((e) => (
              <span
                key={e}
                className="text-xs px-2 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--foreground)]"
              >
                {e}
              </span>
            ))}
          </div>
        </Section>
      )}

      {opinion.key_quotes.length > 0 && (
        <Section title="Key Quotes">
          <ul className="flex flex-col gap-2">
            {opinion.key_quotes.map((q, idx) => (
              <li
                key={`${q.agent_id}-${idx}`}
                className="text-sm italic border-l-2 border-[var(--border)] pl-3 text-[var(--muted-foreground)]"
              >
                "{q.content}"
                <span className="ml-2 not-italic text-xs">
                  — {q.agent_id.slice(0, 8)}, step {q.step}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1">
        {title}
      </div>
      {children}
    </div>
  );
}
