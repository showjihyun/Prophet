/**
 * SimulationReportModal — Summary report shown when simulation completes.
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-report
 */
import { useNavigate } from "react-router-dom";
import { X, Download, RotateCcw, TrendingUp } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from "../../api/client";
import type { StepResult } from "../../types/simulation";
import HelpTooltip, { type TooltipAlign } from "./HelpTooltip";
import type { GlossaryTerm } from "@/config/glossary";

interface Props {
  onClose: () => void;
}

// All term explanations live in @/config/glossary — see HelpTooltip usage below.

function deriveReport(steps: StepResult[]) {
  if (steps.length === 0) return null;

  const last = steps[steps.length - 1];
  const first = steps[0];

  // Final adoption rate (%)
  const finalAdoptionRate = Math.round((last.adoption_rate ?? 0) * 100);

  // Final sentiment
  const finalSentiment = last.mean_sentiment ?? 0;

  // Count emergent events from steps
  const totalEmergentEvents = steps.reduce(
    (sum, s) => sum + (s.emergent_events?.length ?? 0),
    0
  );

  // Top community by adoption rate in final step
  const communityMetrics = last.community_metrics ?? {};
  let topCommunity = "—";
  let topRate = 0;
  for (const [cid, m] of Object.entries(communityMetrics)) {
    if ((m.adoption_rate ?? 0) > topRate) {
      topRate = m.adoption_rate ?? 0;
      topCommunity = cid;
    }
  }

  // Adoption curve: sample up to 20 data points
  const sampleInterval = Math.max(1, Math.floor(steps.length / 20));
  const curve = steps
    .filter((_, i) => i % sampleInterval === 0 || i === steps.length - 1)
    .map((s) => ({
      step: s.step,
      rate: Math.round((s.adoption_rate ?? 0) * 100),
    }));

  // Key events timeline: first 5 emergent events
  const keyEvents: Array<{ step: number; type: string; description: string }> = [];
  for (const s of steps) {
    for (const e of s.emergent_events ?? []) {
      if (keyEvents.length >= 5) break;
      keyEvents.push({ step: s.step, type: e.event_type, description: e.description });
    }
    if (keyEvents.length >= 5) break;
  }

  return {
    totalSteps: last.step,
    initialAdoptionRate: Math.round((first.adoption_rate ?? 0) * 100),
    finalAdoptionRate,
    finalSentiment: finalSentiment.toFixed(2),
    totalEmergentEvents,
    topCommunity,
    topCommunityRate: Math.round(topRate * 100),
    curve,
    keyEvents,
  };
}

export default function SimulationReportModal({ onClose }: Props) {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const steps = useSimulationStore((s) => s.steps);

  const report = deriveReport(steps);

  if (!report) return null;

  const maxCurveRate = Math.max(...report.curve.map((p) => p.rate), 1);

  const sentimentColor =
    Number(report.finalSentiment) > 0.5
      ? "text-[var(--sentiment-positive)]"
      : Number(report.finalSentiment) < -0.5
        ? "text-[var(--sentiment-negative)]"
        : "text-[var(--muted-foreground)]";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="relative w-full max-w-2xl mx-4 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[var(--sentiment-positive)]" />
            <h2 className="text-base font-semibold text-[var(--foreground)]">
              Simulation Complete — Summary Report
            </h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-[var(--secondary)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 flex flex-col gap-5 max-h-[75vh] overflow-y-auto">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard
              label="Total Steps"
              value={String(report.totalSteps)}
              term="totalSteps"
            />
            <MetricCard
              label="Final Adoption"
              value={`${report.finalAdoptionRate}%`}
              accent="positive"
              term="finalAdoption"
            />
            <MetricCard
              label="Final Sentiment"
              value={report.finalSentiment}
              className={sentimentColor}
              term="finalSentiment"
            />
            <MetricCard
              label="Emergent Events"
              value={String(report.totalEmergentEvents)}
              accent={report.totalEmergentEvents > 0 ? "warning" : undefined}
              term="emergentEvents"
              tooltipAlign="right"
            />
          </div>

          {/* Top Community */}
          <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-3">
            <p className="text-xs font-medium text-[var(--muted-foreground)] mb-0.5 flex items-center gap-1.5">
              Top Community by Adoption
              <HelpTooltip term="topCommunity" />
            </p>
            <p className="text-sm font-semibold text-[var(--foreground)]">
              {report.topCommunity}{" "}
              <span className="font-normal text-[var(--muted-foreground)]">
                — {report.topCommunityRate}% adopted
              </span>
            </p>
          </div>

          {/* Adoption Curve */}
          <div>
            <p className="text-xs font-medium text-[var(--muted-foreground)] mb-2 flex items-center gap-1.5">
              Adoption Curve
              <HelpTooltip term="adoptionCurve" />
            </p>
            <div className="flex items-end gap-0.5 h-20 w-full">
              {report.curve.map((p, i) => (
                <div
                  key={i}
                  title={`Step ${p.step}: ${p.rate}%`}
                  className="flex-1 rounded-t-sm bg-[var(--primary)] opacity-80 hover:opacity-100 transition-opacity min-w-[2px]"
                  style={{
                    height: `${Math.max(2, (p.rate / maxCurveRate) * 100)}%`,
                  }}
                />
              ))}
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-[var(--muted-foreground)]">
              <span>Step 0</span>
              <span>Step {report.totalSteps}</span>
            </div>
          </div>

          {/* Key Events Timeline */}
          {report.keyEvents.length > 0 && (
            <div>
              <p className="text-xs font-medium text-[var(--muted-foreground)] mb-2 flex items-center gap-1.5">
                Key Events
                <HelpTooltip term="keyEvents" />
              </p>
              <div className="flex flex-col gap-2">
                {report.keyEvents.map((e, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 text-xs"
                  >
                    <span className="shrink-0 font-mono text-[var(--muted-foreground)] w-14">
                      Step {e.step}
                    </span>
                    <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--secondary)] text-[var(--foreground)] uppercase">
                      {(e.type ?? "event").replace(/_/g, " ")}
                    </span>
                    <span className="text-[var(--muted-foreground)] line-clamp-1">
                      {e.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--border)] bg-[var(--background)]">
          <div className="flex items-center gap-2">
            <button
              onClick={() => simulation && apiClient.simulations.export(simulation.simulation_id, "json")}
              disabled={!simulation}
              className="h-8 px-3 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--secondary)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              Export JSON
            </button>
            <button
              onClick={() => simulation && apiClient.simulations.export(simulation.simulation_id, "csv")}
              disabled={!simulation}
              className="h-8 px-3 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--secondary)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="h-8 px-3 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--secondary)] transition-colors"
            >
              Close
            </button>
            <button
              onClick={() => { onClose(); navigate("/setup"); }}
              className="h-8 px-3 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Run Again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent,
  className,
  term,
  tooltipAlign = "center",
}: {
  label: string;
  value: string;
  accent?: "positive" | "warning";
  className?: string;
  term?: GlossaryTerm;
  tooltipAlign?: TooltipAlign;
}) {
  const valueColor =
    accent === "positive"
      ? "text-[var(--sentiment-positive)]"
      : accent === "warning"
        ? "text-[var(--sentiment-warning)]"
        : className ?? "text-[var(--foreground)]";

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-3 flex flex-col gap-1">
      <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted-foreground)] flex items-center gap-1.5">
        <span>{label}</span>
        {term && <HelpTooltip term={term} align={tooltipAlign} />}
      </p>
      <p className={`text-xl font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}
