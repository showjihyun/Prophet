/**
 * OverallOpinionPanel — Cross-community EliteLLM narrative.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
 *
 * The "big picture" version of EliteLLMNarrativePanel: one headline
 * narrative explaining how the campaign played out across the whole
 * simulation, plus a collapsible per-community breakdown.
 *
 * Usage: mount on a post-simulation page (dashboard / results view)
 * where the user wants to see the whole-simulation story without
 * clicking into each community individually.
 */
import { useState } from "react";
import { useOverallOpinionSynthesis } from "@/api/queries";
import type { CommunityOpinion, OverallOpinion } from "@/types/api";

interface Props {
  simulationId: string | null;
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

export default function OverallOpinionPanel({ simulationId }: Props) {
  const mutation = useOverallOpinionSynthesis(simulationId);
  const data: OverallOpinion | undefined = mutation.data;
  const canRun = Boolean(simulationId) && !mutation.isPending;

  return (
    <div
      data-testid="overall-opinion-panel"
      className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Whole-Simulation Narrative
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
            EliteLLM-synthesised cross-community explanation — why this
            simulation ended where it did. Also synthesises each community
            individually as a side-effect, so you can drill down without a
            second round-trip.
          </p>
        </div>
        <button
          type="button"
          disabled={!canRun}
          onClick={() => mutation.mutate()}
          className="text-xs px-3 py-1.5 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {mutation.isPending
            ? "Synthesising…"
            : data
              ? "Refresh"
              : "Synthesise Whole Simulation"}
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

      {!data && !mutation.isPending && !mutation.isError && (
        <p className="text-sm text-[var(--muted-foreground)]">
          Click <span className="font-medium">Synthesise Whole Simulation</span>{" "}
          to generate a cross-community narrative plus one summary per
          community. Results are cached per step.
        </p>
      )}

      {data && <OverallBody data={data} />}
    </div>
  );
}

function OverallBody({ data }: { data: OverallOpinion }) {
  const { overall, communities } = data;
  const [expanded, setExpanded] = useState(true);

  const trendLabel =
    SENTIMENT_LABEL[overall.sentiment_trend] ?? overall.sentiment_trend;
  const trendColor =
    SENTIMENT_COLOR[overall.sentiment_trend] ?? "var(--muted-foreground)";

  return (
    <div className="flex flex-col gap-5">
      {overall.is_fallback_stub && (
        <div className="text-xs px-2 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-600">
          Fallback stub — every configured LLM adapter failed, so this is a
          rule-engine placeholder rather than a real LLM completion.
        </div>
      )}

      {/* Headline */}
      <section>
        <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1">
          Headline
        </div>
        <p className="text-base text-[var(--foreground)] leading-relaxed">
          {overall.summary}
        </p>
        <div className="flex items-center gap-2 text-xs mt-2">
          <span className="text-[var(--muted-foreground)]">Trend:</span>
          <span className="font-medium" style={{ color: trendColor }}>
            {trendLabel}
          </span>
          <span className="text-[var(--muted-foreground)]">·</span>
          <span className="text-[var(--muted-foreground)]">
            {overall.source_agent_count} agents across {communities.length}{" "}
            communities
          </span>
          <span className="text-[var(--muted-foreground)]">·</span>
          <span className="text-[var(--muted-foreground)]">
            {overall.llm_provider}/{overall.llm_model}
          </span>
        </div>
      </section>

      {overall.themes.length > 0 && (
        <Section title="Cross-Community Themes">
          <ul className="flex flex-col gap-1">
            {overall.themes.map((t, idx) => (
              <li
                key={`${t.theme}-${idx}`}
                className="flex items-baseline gap-2 text-sm"
              >
                <span className="inline-block w-12 text-right text-xs tabular-nums text-[var(--muted-foreground)]">
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

      {overall.divisions.length > 0 && (
        <Section title="Faction Contrasts">
          <ul className="flex flex-col gap-1">
            {overall.divisions.map((d, idx) => (
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

      {/* Per-community breakdown */}
      {communities.length > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setExpanded((x) => !x)}
            className="w-full flex items-center justify-between text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-2 hover:text-[var(--foreground)]"
          >
            <span>Per-Community Breakdown ({communities.length})</span>
            <span>{expanded ? "▼" : "▶"}</span>
          </button>
          {expanded && (
            <div className="flex flex-col gap-3">
              {communities.map((c) => (
                <CommunityCard key={c.community_id} community={c} />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function CommunityCard({ community }: { community: CommunityOpinion }) {
  const trendColor =
    SENTIMENT_COLOR[community.sentiment_trend] ?? "var(--muted-foreground)";
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--background)] p-3">
      <div className="flex items-center justify-between mb-1.5">
        <h4 className="font-medium text-sm text-[var(--foreground)]">
          {community.community_id}
        </h4>
        <span className="text-xs font-medium" style={{ color: trendColor }}>
          {community.sentiment_trend}
        </span>
      </div>
      <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
        {community.summary}
      </p>
      {community.dominant_emotions.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {community.dominant_emotions.map((e) => (
            <span
              key={e}
              className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--secondary)] text-[var(--muted-foreground)]"
            >
              {e}
            </span>
          ))}
        </div>
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
    <section>
      <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1">
        {title}
      </div>
      {children}
    </section>
  );
}
