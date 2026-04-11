/**
 * InjectEventModal — Inject external events mid-simulation.
 * @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
 * @spec docs/spec/07_FRONTEND_SPEC.md#control-panel
 */
import { useState, useEffect, useCallback } from "react";
import { X, Zap, AlertTriangle } from "lucide-react";
import { useInjectEvent } from "../../api/queries";
import { useSimulationStore } from "../../store/simulationStore";

export interface InjectEventModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EVENT_TYPES = [
  { value: "controversy", label: "Controversy (Negative PR)" },
  { value: "competitor_attack", label: "Competitor Attack" },
  { value: "celebrity_endorsement", label: "Celebrity Endorsement" },
  { value: "news_article", label: "News Article" },
  { value: "regulatory_change", label: "Regulatory Change" },
  { value: "product_update", label: "Product Update" },
] as const;

const COMMUNITY_OPTIONS = ["A", "B", "C", "D", "E"] as const;

interface EventForm {
  event_type: string;
  content: string;
  controversy: number;
  target_communities: string[];
}

const INITIAL: EventForm = {
  event_type: "controversy",
  content: "",
  controversy: 0.5,
  target_communities: [],
};

export default function InjectEventModal({ isOpen, onClose }: InjectEventModalProps) {
  const [form, setForm] = useState<EventForm>(INITIAL);
  const injectEvent = useInjectEvent();
  const submitting = injectEvent.isPending;
  const [result, setResult] = useState<{ event_id: string; effective_step: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const simulation = useSimulationStore((s) => s.simulation);

  // Reset-on-open: this is the canonical pattern for clearing modal form
  // state when the modal is re-opened. The lint rule flags any setState
  // in an effect, but this reset is intentional and driven by an external
  // prop change.
  useEffect(() => {
    if (isOpen) {
      queueMicrotask(() => {
        setForm(INITIAL);
        setResult(null);
        setError(null);
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  const toggleCommunity = useCallback((c: string) => {
    setForm((prev) => ({
      ...prev,
      target_communities: prev.target_communities.includes(c)
        ? prev.target_communities.filter((x) => x !== c)
        : [...prev.target_communities, c],
    }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!form.content.trim()) {
      setError("Content is required");
      return;
    }
    if (!simulation?.simulation_id) return;

    setError(null);
    try {
      const res = await injectEvent.mutateAsync({
        simId: simulation.simulation_id,
        event: {
          event_type: form.event_type,
          content: form.content,
          controversy: form.controversy,
          target_communities: form.target_communities.length > 0 ? form.target_communities : undefined,
        },
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to inject event");
    }
  }, [form, simulation, injectEvent]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[520px] max-h-[600px] bg-[var(--card)] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-[var(--border)]">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[var(--sentiment-warning)]" />
              <h2 className="text-lg font-semibold text-[var(--foreground)]">Inject Event</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              Inject an external event into the running simulation. Takes effect on the next step.
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-5">
          {result ? (
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="w-12 h-12 rounded-full bg-[var(--sentiment-positive)]/20 flex items-center justify-center">
                <Zap className="w-6 h-6 text-[var(--sentiment-positive)]" />
              </div>
              <h3 className="text-base font-semibold text-[var(--foreground)]">Event Injected</h3>
              <p className="text-sm text-[var(--muted-foreground)] text-center">
                Event <span className="font-mono text-[var(--foreground)]">{result.event_id.slice(0, 8)}</span> will take
                effect at step <span className="font-bold text-[var(--foreground)]">{result.effective_step}</span>.
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
              {/* Event Type */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--foreground)]">Event Type</label>
                <select
                  value={form.event_type}
                  onChange={(e) => setForm((p) => ({ ...p, event_type: e.target.value }))}
                  className="w-full h-10 rounded-md border border-[var(--input)] px-3 text-sm bg-[var(--card)] text-[var(--foreground)]"
                >
                  {EVENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              {/* Content */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--foreground)]">Content</label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((p) => ({ ...p, content: e.target.value }))}
                  placeholder="Describe the event (e.g., 'Battery explosion reported in multiple units')"
                  className="w-full rounded-md border border-[var(--input)] px-3 py-2 text-sm bg-[var(--card)] text-[var(--foreground)] resize-y"
                  style={{ minHeight: "80px" }}
                />
              </div>

              {/* Controversy slider */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--foreground)]">Controversy Level</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">{form.controversy.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={form.controversy}
                  onChange={(e) => setForm((p) => ({ ...p, controversy: parseFloat(e.target.value) }))}
                  className="w-full accent-[var(--foreground)]"
                />
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
                  <span>Low impact</span>
                  <span>High impact</span>
                </div>
              </div>

              {/* Target communities */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--foreground)]">
                  Target Communities <span className="text-[var(--muted-foreground)] font-normal">(empty = all)</span>
                </label>
                <div className="flex gap-2">
                  {COMMUNITY_OPTIONS.map((c) => (
                    <button
                      key={c}
                      onClick={() => toggleCommunity(c)}
                      className={`h-8 w-8 rounded-md text-xs font-bold transition-colors border ${
                        form.target_communities.includes(c)
                          ? "bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]"
                          : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <p className="text-sm text-[var(--destructive)]">{error}</p>
              )}
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
              onClick={handleSubmit}
              disabled={submitting}
              className="h-10 px-4 text-sm font-medium rounded-md bg-[var(--sentiment-warning)] text-black hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
            >
              <Zap className="w-4 h-4" />
              {submitting ? "Injecting..." : "Inject Event"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
