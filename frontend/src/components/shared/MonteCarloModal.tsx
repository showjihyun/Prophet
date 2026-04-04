/**
 * MonteCarloModal — Configure and monitor Monte Carlo analysis jobs.
 * @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idmonte-carlo
 * @spec docs/spec/04_SIMULATION_SPEC.md#monte-carlo
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { X, BarChart3, Loader2 } from "lucide-react";
import { apiClient } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";

export interface MonteCarloModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface MonteCarloResult {
  job_id: string;
  status: string;
  n_runs: number;
  completed_runs?: number;
  viral_probability?: number;
  expected_reach?: number;
  p5_reach?: number;
  p50_reach?: number;
  p95_reach?: number;
  community_adoption?: Record<string, number>;
  error_message?: string;
}

type Phase = "config" | "running" | "completed" | "failed";

export default function MonteCarloModal({ isOpen, onClose }: MonteCarloModalProps) {
  const simulation = useSimulationStore((s) => s.simulation);
  const [nRuns, setNRuns] = useState(100);
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [phase, setPhase] = useState<Phase>("config");
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    if (isOpen) {
      cancelledRef.current = false;
      // Defer setState calls out of the synchronous effect body
      // (react-hooks/set-state-in-effect).
      queueMicrotask(() => {
        setNRuns(100);
        setLlmEnabled(false);
        setPhase("config");
        setResult(null);
        setError(null);
      });
    } else {
      cancelledRef.current = true;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  const pollJob = useCallback(
    (jobId: string) => {
      if (!simulation?.simulation_id) return;
      pollRef.current = setInterval(async () => {
        try {
          const res = (await apiClient.simulations.getMonteCarloJob(
            simulation.simulation_id,
            jobId,
          )) as MonteCarloResult;
          setResult(res);
          if (res.status === "completed") {
            setPhase("completed");
            if (pollRef.current) clearInterval(pollRef.current);
            // Persist MC results for Analytics page
            try { localStorage.setItem(`prophet-mc-${simulationId}`, JSON.stringify(res)); } catch { /* ignore */ }
          } else if (res.status === "failed") {
            setPhase("failed");
            setError(res.error_message || "Job failed");
            if (pollRef.current) clearInterval(pollRef.current);
          }
        } catch {
          /* keep polling */
        }
      }, 2000);
    },
    [simulation],
  );

  const handleStart = useCallback(async () => {
    if (!simulation?.simulation_id) return;
    setPhase("running");
    setError(null);
    try {
      const res = await apiClient.simulations.monteCarlo(simulation.simulation_id, {
        n_runs: nRuns,
        llm_enabled: llmEnabled,
      });
      if (cancelledRef.current) return;
      setResult({ job_id: res.job_id, status: "queued", n_runs: nRuns });
      pollJob(res.job_id);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Failed to start Monte Carlo");
    }
  }, [simulation, nRuns, llmEnabled, pollJob]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[520px] max-h-[650px] bg-[var(--card)] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-[var(--border)]">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[var(--community-delta)]" />
              <h2 className="text-lg font-semibold text-[var(--foreground)]">Monte Carlo Analysis</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              Run N parallel simulations to compute probability distributions.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-5">
          {phase === "config" && (
            <>
              {/* N runs slider */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--foreground)]">Number of Runs</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">{nRuns}</span>
                </div>
                <input
                  type="range"
                  min={10}
                  max={500}
                  step={10}
                  value={nRuns}
                  onChange={(e) => setNRuns(parseInt(e.target.value))}
                  className="w-full accent-[var(--community-delta)]"
                />
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
                  <span>10 (fast)</span>
                  <span>500 (precise)</span>
                </div>
              </div>

              {/* LLM toggle */}
              <div className="flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-[var(--foreground)]">Enable LLM (Tier 3)</span>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    Uses Elite LLM for cognition — slower and costlier
                  </span>
                </div>
                <button
                  role="switch"
                  aria-checked={llmEnabled}
                  onClick={() => setLlmEnabled(!llmEnabled)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                    llmEnabled ? "bg-[var(--community-delta)]" : "bg-[var(--secondary)]"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${
                      llmEnabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Estimate */}
              <div className="p-3 rounded-lg bg-[var(--secondary)]">
                <p className="text-xs text-[var(--muted-foreground)]">
                  Estimated time: ~{Math.ceil(nRuns * (llmEnabled ? 2.5 : 0.3))}s
                  {" | "}Cost: ~${(nRuns * (llmEnabled ? 0.05 : 0.001)).toFixed(2)}
                </p>
              </div>
            </>
          )}

          {phase === "running" && (
            <div className="flex flex-col items-center gap-4 py-8">
              <Loader2 className="w-10 h-10 text-[var(--community-delta)] animate-spin" />
              <h3 className="text-base font-semibold text-[var(--foreground)]">Running Analysis...</h3>
              <p className="text-sm text-[var(--muted-foreground)]">
                {result?.completed_runs ?? 0} / {nRuns} runs completed
              </p>
              <div className="w-full h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
                <div
                  className="h-full bg-[var(--community-delta)] transition-all duration-500"
                  style={{ width: `${((result?.completed_runs ?? 0) / nRuns) * 100}%` }}
                />
              </div>
            </div>
          )}

          {phase === "completed" && result && (
            <div className="flex flex-col gap-4">
              <div className="text-center py-2">
                <h3 className="text-base font-semibold text-[var(--foreground)]">Analysis Complete</h3>
                <p className="text-xs text-[var(--muted-foreground)]">{result.n_runs} runs analyzed</p>
              </div>

              {/* Key metrics */}
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="Viral Probability" value={`${((result.viral_probability ?? 0) * 100).toFixed(1)}%`} />
                <MetricCard label="Expected Reach" value={`${result.expected_reach ?? 0}`} />
                <MetricCard label="P5 Reach" value={`${result.p5_reach ?? 0}`} sub="5th percentile" />
                <MetricCard label="P50 Reach" value={`${result.p50_reach ?? 0}`} sub="Median" />
                <MetricCard label="P95 Reach" value={`${result.p95_reach ?? 0}`} sub="95th percentile" />
              </div>

              {/* Community adoption */}
              {result.community_adoption && (
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-medium text-[var(--muted-foreground)]">Community Adoption</span>
                  <div className="flex flex-col gap-1.5">
                    {Object.entries(result.community_adoption).map(([cid, rate]) => (
                      <div key={cid} className="flex items-center gap-2">
                        <span className="text-xs font-mono text-[var(--foreground)] w-6">{cid}</span>
                        <div className="flex-1 h-3 rounded-full bg-[var(--secondary)] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[var(--community-alpha)] transition-all"
                            style={{ width: `${rate * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-[var(--muted-foreground)] w-12 text-right">
                          {(rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {phase === "failed" && (
            <div className="flex flex-col items-center gap-3 py-6">
              <p className="text-sm text-[var(--destructive)]">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--border)]">
          <button
            onClick={onClose}
            className="h-10 px-4 text-sm font-medium rounded-md border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            {phase === "completed" || phase === "failed" ? "Close" : "Cancel"}
          </button>
          {phase === "config" && (
            <button
              onClick={handleStart}
              className="h-10 px-4 text-sm font-medium rounded-md bg-[var(--community-delta)] text-white hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <BarChart3 className="w-4 h-4" />
              Start Analysis
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="p-3 rounded-lg bg-[var(--secondary)] flex flex-col gap-1">
      <span className="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wider">{label}</span>
      <span className="text-lg font-bold text-[var(--foreground)]">{value}</span>
      {sub && <span className="text-[10px] text-[var(--muted-foreground)]">{sub}</span>}
    </div>
  );
}
