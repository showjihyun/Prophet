/**
 * SimulationReportModal — Summary report shown when simulation completes.
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-report
 */
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { X, Download, RotateCcw, TrendingUp, HelpCircle } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from "../../api/client";
import type { StepResult } from "../../types/simulation";

interface Props {
  onClose: () => void;
}

/**
 * Help tooltip — appears on hover OR on click (mobile-friendly).
 *
 * Anti-flicker design:
 * - Hover handlers live on the WRAPPER span, not the button, so moving the
 *   mouse from icon → tooltip stays inside the same hover region.
 * - The tooltip uses `pointer-events-none` so it never steals hover state
 *   away from the wrapper (the wrapper drives `hovered`).
 * - The tooltip is always rendered (visibility toggled via opacity) so
 *   appearance/disappearance never causes layout reflow.
 * - `align="right"` positions the tooltip flush to the right edge of the
 *   icon, used for cards near the modal's right edge so the 256px tooltip
 *   doesn't overflow the modal and trigger horizontal scrollbar flicker.
 */
function HelpTooltip({
  text,
  label,
  align = "center",
}: {
  text: string;
  label: string;
  align?: "left" | "center" | "right";
}) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const visible = open || hovered;

  const alignClass =
    align === "right"
      ? "right-0"
      : align === "left"
        ? "left-0"
        : "left-1/2 -translate-x-1/2";

  return (
    <span
      ref={ref}
      className="relative inline-flex items-center"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        aria-label={`What does ${label} mean?`}
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        className="inline-flex items-center justify-center w-3.5 h-3.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>
      {/* Always rendered — opacity-toggled to avoid layout reflow */}
      <span
        role="tooltip"
        aria-hidden={!visible}
        className={`absolute z-20 ${alignClass} top-full mt-1.5 w-64 px-3 py-2 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg text-[11px] font-normal leading-relaxed text-[var(--foreground)] whitespace-normal pointer-events-none transition-opacity duration-100 ${visible ? "opacity-100" : "opacity-0"}`}
      >
        <span className="block font-semibold text-[var(--foreground)] mb-1">{label}</span>
        {text}
      </span>
    </span>
  );
}

// English explanations for each metric and section.
const HELP = {
  totalSteps:
    "Number of simulation steps that ran. Each step represents one tick of agent perception, cognition, and action across the entire population.",
  finalAdoption:
    "Percentage of agents that have adopted the campaign / message at the end of the simulation. 100% means everyone adopted, 0% means no one did.",
  finalSentiment:
    "Average sentiment score of all agents at the final step. Range: -1.0 (strongly negative) to +1.0 (strongly positive). 0 is neutral.",
  emergentEvents:
    "Total number of automatically detected behavioral patterns: viral cascade, polarization, echo chamber, collapse, or slow adoption. Higher numbers mean a more dynamic simulation.",
  topCommunity:
    "The community with the highest adoption rate at the end of the simulation. The percentage shows how much of that specific community adopted.",
  adoptionCurve:
    "Adoption rate over time, sampled across the simulation. Bars show the percentage of agents that had adopted at each sampled step. Steeper rises indicate viral spread.",
  keyEvents:
    "Notable behavioral patterns detected during the run, in chronological order. Up to 5 events are shown with their step number and a short description.",
} as const;

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
              tooltip={HELP.totalSteps}
            />
            <MetricCard
              label="Final Adoption"
              value={`${report.finalAdoptionRate}%`}
              accent="positive"
              tooltip={HELP.finalAdoption}
            />
            <MetricCard
              label="Final Sentiment"
              value={report.finalSentiment}
              className={sentimentColor}
              tooltip={HELP.finalSentiment}
            />
            <MetricCard
              label="Emergent Events"
              value={String(report.totalEmergentEvents)}
              accent={report.totalEmergentEvents > 0 ? "warning" : undefined}
              tooltip={HELP.emergentEvents}
              tooltipAlign="right"
            />
          </div>

          {/* Top Community */}
          <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-3">
            <p className="text-xs font-medium text-[var(--muted-foreground)] mb-0.5 flex items-center gap-1.5">
              Top Community by Adoption
              <HelpTooltip label="Top Community by Adoption" text={HELP.topCommunity} />
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
              <HelpTooltip label="Adoption Curve" text={HELP.adoptionCurve} />
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
                <HelpTooltip label="Key Events" text={HELP.keyEvents} />
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
  tooltip,
  tooltipAlign = "center",
}: {
  label: string;
  value: string;
  accent?: "positive" | "warning";
  className?: string;
  tooltip?: string;
  tooltipAlign?: "left" | "center" | "right";
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
        {tooltip && <HelpTooltip label={label} text={tooltip} align={tooltipAlign} />}
      </p>
      <p className={`text-xl font-bold ${valueColor}`}>{value}</p>
    </div>
  );
}
