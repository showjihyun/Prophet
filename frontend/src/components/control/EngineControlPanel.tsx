/**
 * EngineControlPanel — SLM/LLM ratio slider + 4-indicator impact display.
 * @spec docs/spec/07_FRONTEND_SPEC.md#control-panel
 * @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idengine-control
 */
import { useState, useCallback } from "react";
import { Cpu, DollarSign, Gauge, Brain, Zap, X } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { useEngineControl } from "../../api/queries";
import type { TierDistribution, EngineImpactReport } from "../../types/simulation";
import { SIM_STATUS } from "@/config/constants";

interface EngineControlResponse {
  tier_distribution: TierDistribution;
  impact_assessment: EngineImpactReport;
}

export interface EngineControlPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function EngineControlPanel({ isOpen, onClose }: EngineControlPanelProps) {
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const slmLlmRatio = useSimulationStore((s) => s.slmLlmRatio);
  const setSlmLlmRatio = useSimulationStore((s) => s.setSlmLlmRatio);
  const [budgetUsd, setBudgetUsd] = useState(50);
  const engineControl = useEngineControl();
  const applying = engineControl.isPending;
  const [error, setError] = useState<string | null>(null);
  const [impact, setImpact] = useState<EngineImpactReport | null>(null);
  const [tierDist, setTierDist] = useState<TierDistribution | null>(null);

  const isPaused = status === SIM_STATUS.PAUSED;

  const handleApply = useCallback(async () => {
    if (!simulation?.simulation_id || !isPaused) return;
    setError(null);
    try {
      const res = (await engineControl.mutateAsync({
        simId: simulation.simulation_id,
        body: { slm_llm_ratio: slmLlmRatio, budget_usd: budgetUsd },
      })) as unknown as EngineControlResponse;
      setImpact(res.impact_assessment);
      setTierDist(res.tier_distribution);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply");
    }
  }, [simulation, slmLlmRatio, budgetUsd, isPaused, engineControl]);

  // Derive labels from ratio
  const slmPct = Math.round(slmLlmRatio * 100);
  const modeLabel = slmLlmRatio < 0.3 ? "Quality" : slmLlmRatio > 0.7 ? "Speed" : "Balanced";

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="engine-control-title"
      onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[400px] bg-[var(--card)] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[var(--muted-foreground)]" />
            <h2 id="engine-control-title" className="text-lg font-semibold text-[var(--foreground)]">Engine Control</h2>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-col gap-3 p-6">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--muted-foreground)]">Mode</span>
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
              modeLabel === "Speed" ? "bg-[var(--sentiment-positive)]/20 text-[var(--sentiment-positive)]" :
              modeLabel === "Quality" ? "bg-[var(--community-delta)]/20 text-[var(--community-delta)]" :
              "bg-[var(--sentiment-warning)]/20 text-[var(--sentiment-warning)]"
            }`}>
              {modeLabel}
            </span>
          </div>

          {/* SLM/LLM Ratio slider */}
          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
              <span>LLM (Quality)</span>
              <span>{slmPct}% SLM</span>
              <span>SLM (Speed)</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={slmLlmRatio}
              onChange={(e) => setSlmLlmRatio(parseFloat(e.target.value))}
              className="w-full accent-[var(--foreground)]"
              disabled={!isPaused}
            />
          </div>

          {/* Budget */}
          <div className="flex items-center gap-2">
            <DollarSign className="w-3 h-3 text-[var(--muted-foreground)]" />
            <span className="text-[10px] text-[var(--muted-foreground)]">Budget</span>
            <input
              type="number"
              min={0}
              step={5}
              value={budgetUsd}
              onChange={(e) => setBudgetUsd(Math.max(0, parseFloat(e.target.value) || 0))}
              className="w-16 h-6 text-xs text-right rounded border border-[var(--border)] bg-[var(--card)] px-1 text-[var(--foreground)]"
              disabled={!isPaused}
            />
            <span className="text-[10px] text-[var(--muted-foreground)]">USD</span>
          </div>

          {/* Apply button */}
          <button
            onClick={handleApply}
            disabled={!isPaused || applying}
            className="h-7 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity disabled:opacity-40 flex items-center justify-center gap-1"
          >
            {applying ? "Applying..." : isPaused ? "Apply" : "Pause to adjust"}
          </button>

          {error && <p className="text-[10px] text-[var(--destructive)]">{error}</p>}

          {/* 4-Indicator Impact Display */}
          {(impact || tierDist) && (
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[var(--border)]">
              <ImpactIndicator
                icon={<DollarSign className="w-3 h-3" />}
                label="Cost / Step"
                value={impact?.cost_efficiency || `$${tierDist?.estimated_cost_per_step?.toFixed(2) ?? "—"}`}
              />
              <ImpactIndicator
                icon={<Brain className="w-3 h-3" />}
                label="Reasoning"
                value={impact?.reasoning_depth || modeLabel}
              />
              <ImpactIndicator
                icon={<Gauge className="w-3 h-3" />}
                label="Velocity"
                value={impact?.simulation_velocity || `${tierDist?.estimated_latency_ms?.toFixed(0) ?? "—"}ms`}
              />
              <ImpactIndicator
                icon={<Zap className="w-3 h-3" />}
                label="Prediction"
                value={impact?.prediction_type || (slmLlmRatio > 0.7 ? "Quantitative" : slmLlmRatio < 0.3 ? "Qualitative" : "Hybrid")}
              />
            </div>
          )}

          {/* Tier distribution */}
          {tierDist && (
            <div className="flex gap-1 text-[10px]">
              <span className="px-1.5 py-0.5 rounded bg-[var(--community-alpha)]/20 text-[var(--community-alpha)]">
                T1: {tierDist.tier1_count}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-[var(--sentiment-warning)]/20 text-[var(--sentiment-warning)]">
                T2: {tierDist.tier2_count}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-[var(--community-delta)]/20 text-[var(--community-delta)]">
                T3: {tierDist.tier3_count}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ImpactIndicator({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 p-1.5 rounded bg-[var(--card)]">
      <span className="text-[var(--muted-foreground)]">{icon}</span>
      <div className="flex flex-col">
        <span className="text-[9px] text-[var(--muted-foreground)]">{label}</span>
        <span className="text-[11px] font-medium text-[var(--foreground)] truncate">{value}</span>
      </div>
    </div>
  );
}
