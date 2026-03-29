/**
 * ReplayModal — Replay simulation from a specific step (creates branch).
 * @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idreplaystep
 * @spec docs/spec/04_SIMULATION_SPEC.md#replay
 */
import { useState, useEffect, useCallback } from "react";
import { X, Rewind, GitBranch } from "lucide-react";
import { apiClient } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";

export interface ReplayModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ReplayModal({ isOpen, onClose }: ReplayModalProps) {
  const simulation = useSimulationStore((s) => s.simulation);
  const currentStep = useSimulationStore((s) => s.currentStep);
  const [targetStep, setTargetStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ replay_id: string; from_step: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const maxStep = currentStep || simulation?.current_step || 1;

  useEffect(() => {
    if (isOpen) {
      setTargetStep(Math.max(1, maxStep - 1));
      setResult(null);
      setError(null);
    }
  }, [isOpen, maxStep]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  const handleReplay = useCallback(async () => {
    if (!simulation?.simulation_id) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiClient.simulations.replay(simulation.simulation_id, targetStep);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create replay branch");
    } finally {
      setSubmitting(false);
    }
  }, [simulation, targetStep]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[440px] bg-[var(--card)] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-[var(--border)]">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Rewind className="w-5 h-5 text-[var(--community-alpha)]" />
              <h2 className="text-lg font-semibold text-[var(--foreground)]">Replay from Step</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              Creates a new branch — original history is preserved.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 flex flex-col gap-5">
          {result ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="w-12 h-12 rounded-full bg-[var(--community-alpha)]/20 flex items-center justify-center">
                <GitBranch className="w-6 h-6 text-[var(--community-alpha)]" />
              </div>
              <h3 className="text-base font-semibold text-[var(--foreground)]">Branch Created</h3>
              <p className="text-sm text-[var(--muted-foreground)] text-center">
                Replay branch <span className="font-mono text-[var(--foreground)]">{result.replay_id.slice(0, 8)}</span>{" "}
                created from step <span className="font-bold text-[var(--foreground)]">{result.from_step}</span>.
              </p>
              <button
                onClick={onClose}
                className="mt-2 h-9 px-4 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
              >
                Close
              </button>
            </div>
          ) : (
            <>
              {/* Step selector */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--foreground)]">Target Step</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">
                    {targetStep} / {maxStep}
                  </span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={maxStep}
                  value={targetStep}
                  onChange={(e) => setTargetStep(parseInt(e.target.value))}
                  className="w-full accent-[var(--community-alpha)]"
                />
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
                  <span>Step 1</span>
                  <span>Step {maxStep}</span>
                </div>
              </div>

              {/* Visual indicator */}
              <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--secondary)]">
                <GitBranch className="w-4 h-4 text-[var(--muted-foreground)] shrink-0" />
                <p className="text-xs text-[var(--muted-foreground)]">
                  Simulation will be replayed from <span className="text-[var(--foreground)] font-medium">step {targetStep}</span>.
                  All agent states will be restored to that checkpoint. A new branch will be created.
                </p>
              </div>

              {error && <p className="text-sm text-[var(--destructive)]">{error}</p>}
            </>
          )}
        </div>

        {/* Footer */}
        {!result && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[var(--border)]">
            <button
              onClick={onClose}
              className="h-10 px-4 text-sm font-medium rounded-md border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleReplay}
              disabled={submitting}
              className="h-10 px-4 text-sm font-medium rounded-md bg-[var(--community-alpha)] text-white hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
            >
              <Rewind className="w-4 h-4" />
              {submitting ? "Creating..." : "Replay"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
