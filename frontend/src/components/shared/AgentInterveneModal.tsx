/**
 * AgentInterveneModal -- Modal dialog for applying interventions to agents.
 * @spec docs/spec/ui/UI_10_AGENT_INTERVENE.md
 */
import { useState, useCallback, useEffect } from "react";
import { X, Zap } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface AgentInterveneModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
  agentLabel: string;
}

interface InterventionState {
  type: string;
  targetScope: string;
  duration: number;
  strength: number;
  message: string;
  notifyConnected: boolean;
  logIntervention: boolean;
  overrideTier: boolean;
}

const INITIAL_STATE: InterventionState = {
  type: "",
  targetScope: "individual",
  duration: 100,
  strength: 0.75,
  message: "",
  notifyConnected: true,
  logIntervention: true,
  overrideTier: false,
};

const INTERVENTION_TYPES = [
  { value: "", label: "Select intervention type..." },
  { value: "inject_message", label: "Inject Message" },
  { value: "modify_sentiment", label: "Modify Sentiment" },
  { value: "change_community", label: "Change Community" },
  { value: "boost_influence", label: "Boost Influence" },
] as const;

const TARGET_SCOPES = [
  { value: "individual", label: "Individual Agent" },
  { value: "community", label: "Community" },
  { value: "neighbors", label: "Network Neighbors" },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function AgentInterveneModal({
  isOpen,
  onClose,
  agentId,
  agentLabel,
}: AgentInterveneModalProps) {
  const [state, setState] = useState<InterventionState>(INITIAL_STATE);

  // Reset form state when modal opens
  useEffect(() => {
    if (isOpen) {
      setState(INITIAL_STATE);
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const updateField = useCallback(
    <K extends keyof InterventionState>(key: K, value: InterventionState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleApply = useCallback(() => {
    // Validation
    if (!state.type) {
      console.warn("[Intervene] Intervention type is required.");
      return;
    }
    if (state.duration < 1) {
      console.warn("[Intervene] Duration must be >= 1.");
      return;
    }
    if (state.strength < 0 || state.strength > 1) {
      console.warn("[Intervene] Strength must be between 0 and 1.");
      return;
    }

    // Future: call apiClient intervention endpoint when available
    onClose();
  }, [state, agentLabel, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={`Intervene on ${agentLabel}`}
    >
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div
        className="relative w-[560px] max-h-[700px] bg-[var(--card)] rounded-xl shadow-2xl flex flex-col overflow-hidden"
        style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.2)" }}
      >
        {/* Header */}
        <div
          className="flex flex-col gap-1 px-6 pt-6 pb-4 border-b"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex items-start justify-between">
            <h2 className="text-lg font-semibold text-[var(--foreground)]">
              Intervene on Agent #{agentId}
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-gray-100 transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-[var(--muted-foreground)]">
            Configure and apply an intervention to modify this agent's behavior
            during simulation.
          </p>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-5">
          {/* Intervention Type */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Intervention Type
            </label>
            <select
              value={state.type}
              onChange={(e) => updateField("type", e.target.value)}
              className="w-full h-10 rounded-md border px-3 text-sm bg-[var(--card)]"
              style={{ borderColor: "var(--input)" }}
            >
              {INTERVENTION_TYPES.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.value === ""}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Target Scope */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Target Scope
            </label>
            <select
              value={state.targetScope}
              onChange={(e) => updateField("targetScope", e.target.value)}
              className="w-full h-10 rounded-md border px-3 text-sm bg-[var(--card)]"
              style={{ borderColor: "var(--input)" }}
            >
              {TARGET_SCOPES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Parameters Row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--foreground)]">
                Duration (steps)
              </label>
              <input
                type="number"
                min={1}
                value={state.duration}
                onChange={(e) =>
                  updateField("duration", Math.max(1, parseInt(e.target.value) || 1))
                }
                className="w-full h-10 rounded-md border px-3 text-sm"
                style={{ borderColor: "var(--input)" }}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-[var(--foreground)]">
                Strength (0-1)
              </label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={state.strength}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  updateField("strength", isNaN(val) ? 0 : val);
                }}
                className="w-full h-10 rounded-md border px-3 text-sm"
                style={{
                  borderColor:
                    state.strength < 0 || state.strength > 1
                      ? "#ef4444"
                      : "var(--input)",
                }}
              />
            </div>
          </div>

          {/* Message / Prompt */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Intervention Message / Prompt
            </label>
            <textarea
              value={state.message}
              onChange={(e) => updateField("message", e.target.value)}
              placeholder="Enter the content or instructions..."
              className="w-full rounded-md border px-3 py-2 text-sm resize-y"
              style={{
                minHeight: "100px",
                borderColor: "var(--input)",
              }}
            />
          </div>

          {/* Options */}
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Options
            </label>

            {/* Notify checkbox */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={state.notifyConnected}
                onChange={(e) => updateField("notifyConnected", e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 accent-[var(--foreground)]"
              />
              <span className="text-sm text-[var(--foreground)]">
                Notify connected agents of intervention
              </span>
            </label>

            {/* Log checkbox */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={state.logIntervention}
                onChange={(e) => updateField("logIntervention", e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 accent-[var(--foreground)]"
              />
              <span className="text-sm text-[var(--foreground)]">
                Log intervention in cascade analytics
              </span>
            </label>

            {/* Tier Override toggle */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm text-[var(--foreground)]">
                  Override Prophet Tier (force LLM)
                </span>
                {state.overrideTier && (
                  <span className="text-xs text-amber-500 mt-0.5">
                    This will use Tier 3 (Elite LLM) regardless of agent tier
                    assignment.
                  </span>
                )}
              </div>
              <button
                role="switch"
                aria-checked={state.overrideTier}
                onClick={() => updateField("overrideTier", !state.overrideTier)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                  state.overrideTier ? "bg-[var(--foreground)]" : "bg-gray-200"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-[var(--card)] shadow-sm ring-0 transition-transform ${
                    state.overrideTier ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-end gap-3 px-6 py-4 border-t"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            onClick={onClose}
            className="h-10 px-4 text-sm font-medium rounded-md border border-[var(--border)] text-[var(--foreground)] hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="h-10 px-4 text-sm font-medium rounded-md bg-[var(--foreground)] text-white hover:bg-[var(--foreground)]/90 transition-colors flex items-center gap-2"
          >
            <Zap className="w-4 h-4" />
            Apply Intervention
          </button>
        </div>
      </div>
    </div>
  );
}
