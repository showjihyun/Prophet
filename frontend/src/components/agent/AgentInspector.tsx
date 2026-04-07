/**
 * AgentInspector — Right drawer showing agent details when a node is clicked.
 * @spec docs/spec/07_FRONTEND_SPEC.md#agentinspector-right-drawer
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { X, User, Cpu, Activity, Brain, Clock } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from "../../api/client";
import type { AgentDetail } from "../../api/client";

interface AgentInspectorProps {
  agentId: string;
  simulationId: string;
  isPaused: boolean;
}

/** Clamp a value to [0, 1] for bar display. */
function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

/** Map belief (-1 to +1) to a 0–100 gauge percentage. */
function beliefToPercent(belief: number): number {
  return Math.round(((belief + 1) / 2) * 100);
}

/** Color for belief gauge fill. */
function beliefColor(belief: number): string {
  if (belief > 0.3) return "var(--sentiment-positive)";
  if (belief < -0.3) return "var(--sentiment-negative)";
  return "var(--muted-foreground)";
}

/** Bar for a named trait/emotion value (0–1 scale). */
function TraitBar({
  label,
  value,
  color = "var(--primary)",
}: {
  label: string;
  value: number;
  color?: string;
}) {
  const pct = Math.round(clamp01(value) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[11px] text-[var(--muted-foreground)] capitalize truncate">
        {label.replace(/_/g, " ")}
      </span>
      <div className="flex-1 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-8 text-right text-[11px] font-mono text-[var(--muted-foreground)]">
        {pct}%
      </span>
    </div>
  );
}

/** Edit slider for a personality/emotion trait. */
function EditSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[11px] text-[var(--muted-foreground)] capitalize truncate">
        {label.replace(/_/g, " ")}
      </span>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={clamp01(value)}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="flex-1 accent-[var(--primary)] h-2 cursor-pointer"
      />
      <span className="w-10 text-right text-[11px] font-mono text-[var(--muted-foreground)]">
        {clamp01(value).toFixed(2)}
      </span>
    </div>
  );
}

type FetchState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: AgentDetail };

export default function AgentInspector({
  agentId,
  simulationId,
  isPaused,
}: AgentInspectorProps) {
  const selectAgent = useSimulationStore((s) => s.selectAgent);
  // FE-PERF-01: gate on latestStep, read recent steps lazily
  const latestStep = useSimulationStore((s) => s.latestStep);
  const addToast = useSimulationStore((s) => s.addToast);

  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [editPersonality, setEditPersonality] = useState<Record<string, number>>({});
  const [editEmotion, setEditEmotion] = useState<Record<string, number>>({});
  const [editBelief, setEditBelief] = useState<number>(0);
  const [saving, setSaving] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Fetch agent detail on mount / agentId change
  useEffect(() => {
    setFetchState({ status: "loading" });
    apiClient.agents
      .get(simulationId, agentId)
      .then((data) => {
        setFetchState({ status: "success", data });
        setEditPersonality({ ...data.personality });
        setEditEmotion({ ...data.emotion });
        setEditBelief(data.belief ?? 0);
      })
      .catch((err) =>
        setFetchState({
          status: "error",
          message: err instanceof Error ? err.message : "Failed to load agent",
        })
      );
  }, [simulationId, agentId]);

  // Close drawer when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        selectAgent(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [selectAgent]);

  // Build last-5 action history from steps (FE-PERF-01: memoized, gated on latestStep)
  const actionHistory = useMemo(() => {
    const steps = useSimulationStore.getState().steps;
    return steps
      .slice(-5)
      .reverse()
      .map((s) => ({ step: s.step, action: s.action_distribution }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep]);

  async function handleSave() {
    if (!isPaused) return;
    setSaving(true);
    try {
      await apiClient.agents.modify(simulationId, agentId, {
        personality: editPersonality,
        emotion: editEmotion,
        belief: editBelief,
      });
      addToast({ type: "success", message: "Agent updated successfully" });
    } catch {
      addToast({ type: "error", message: "Failed to save agent changes" });
    } finally {
      setSaving(false);
    }
  }

  const agent = fetchState.status === "success" ? fetchState.data : null;

  // Personality axes order
  const PERSONALITY_KEYS = [
    "openness",
    "skepticism",
    "trend_following",
    "brand_loyalty",
    "social_influence",
  ];

  const PERSONALITY_COLORS = [
    "var(--community-alpha)",
    "var(--community-beta)",
    "var(--community-gamma)",
    "var(--community-delta)",
    "var(--community-bridge)",
  ];

  const EMOTION_COLORS: Record<string, string> = {
    interest: "var(--primary)",
    trust: "var(--sentiment-positive)",
    skepticism: "var(--muted-foreground)",
    excitement: "var(--sentiment-warning)",
  };

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 z-40 bg-black/30" />

      {/* Drawer */}
      <div
        ref={drawerRef}
        data-testid="agent-inspector"
        className="fixed right-0 top-0 bottom-0 z-50 w-80 flex flex-col bg-[var(--card)] border-l border-[var(--border)] shadow-2xl overflow-hidden"
        style={{ animation: "slideInRight 0.2s ease-out" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] shrink-0">
          <div className="flex items-center gap-2">
            <User className="w-4 h-4 text-[var(--primary)]" />
            <h2 className="text-sm font-semibold text-[var(--foreground)]">
              Agent Inspector
            </h2>
          </div>
          <button
            onClick={() => selectAgent(null)}
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[var(--secondary)] transition-colors"
            aria-label="Close inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-5">
          {fetchState.status === "loading" && (
            <div className="flex items-center justify-center py-12">
              <span className="text-sm text-[var(--muted-foreground)] animate-pulse">
                Loading agent...
              </span>
            </div>
          )}

          {fetchState.status === "error" && (
            <div className="flex items-center justify-center py-12">
              <span className="text-sm text-[var(--destructive)]">
                {fetchState.message}
              </span>
            </div>
          )}

          {agent && (
            <>
              {/* Identity */}
              <section className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <Cpu className="w-3.5 h-3.5" />
                  Identity
                </div>
                <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] p-3 flex flex-col gap-1.5">
                  <InfoRow label="Agent ID" value={agent.agent_id} mono />
                  <InfoRow label="Type" value={agent.agent_type} />
                  <InfoRow label="Community" value={agent.community_id} mono />
                  <InfoRow
                    label="Status"
                    value={agent.adopted ? "Adopted" : "Not adopted"}
                    valueClass={
                      agent.adopted
                        ? "text-[var(--sentiment-positive)]"
                        : "text-[var(--muted-foreground)]"
                    }
                  />
                  <InfoRow
                    label="Influence"
                    value={`${(agent.influence_score ?? 0).toFixed(3)}`}
                    mono
                  />
                </div>
              </section>

              {/* Belief Gauge */}
              <section className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <Brain className="w-3.5 h-3.5" />
                  Belief
                </div>
                <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] p-3">
                  <div className="flex justify-between text-[10px] text-[var(--muted-foreground)] mb-1.5">
                    <span>−1 (hostile)</span>
                    <span className="font-mono font-semibold text-[var(--foreground)]">
                      {(agent.belief ?? 0).toFixed(3)}
                    </span>
                    <span>+1 (advocate)</span>
                  </div>
                  <div className="relative h-3 rounded-full bg-[var(--secondary)] overflow-hidden">
                    {/* Zero marker */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-[var(--border)]" />
                    <div
                      className="absolute top-0 bottom-0 rounded-full transition-all duration-300"
                      style={{
                        left:
                          agent.belief >= 0
                            ? "50%"
                            : `${beliefToPercent(agent.belief)}%`,
                        right:
                          agent.belief < 0
                            ? "50%"
                            : `${100 - beliefToPercent(agent.belief)}%`,
                        backgroundColor: beliefColor(agent.belief),
                      }}
                    />
                  </div>
                </div>
              </section>

              {/* Personality */}
              <section className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <Activity className="w-3.5 h-3.5" />
                  Personality
                </div>
                <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] p-3 flex flex-col gap-2">
                  {PERSONALITY_KEYS.map((key, idx) => (
                    <TraitBar
                      key={key}
                      label={key}
                      value={(agent.personality ?? {})[key] ?? 0}
                      color={PERSONALITY_COLORS[idx % PERSONALITY_COLORS.length]}
                    />
                  ))}
                </div>
              </section>

              {/* Emotion */}
              <section className="flex flex-col gap-2">
                <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  Emotion State
                </div>
                <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] p-3 flex flex-col gap-2">
                  {Object.entries(agent.emotion ?? {}).map(([key, val]) => (
                    <TraitBar
                      key={key}
                      label={key}
                      value={val}
                      color={EMOTION_COLORS[key] ?? "var(--primary)"}
                    />
                  ))}
                </div>
              </section>

              {/* Action History */}
              <section className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <Clock className="w-3.5 h-3.5" />
                  Action History (last 5 steps)
                </div>
                <div className="rounded-lg bg-[var(--background)] border border-[var(--border)] divide-y divide-[var(--border)]">
                  {actionHistory.length === 0 ? (
                    <div className="px-3 py-3 text-xs text-[var(--muted-foreground)] italic">
                      No steps recorded yet
                    </div>
                  ) : (
                    actionHistory.map(({ step, action }) => {
                      const topAction = Object.entries(action).sort(
                        (a, b) => b[1] - a[1]
                      )[0];
                      return (
                        <div
                          key={step}
                          className="flex items-center justify-between px-3 py-2"
                        >
                          <span className="text-[11px] font-mono text-[var(--muted-foreground)]">
                            Step {step}
                          </span>
                          <span className="text-[11px] font-medium text-[var(--foreground)] capitalize">
                            {topAction
                              ? `${topAction[0].replace(/_/g, " ")} (${topAction[1]})`
                              : "—"}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              </section>

              {/* Edit Panel — only when PAUSED */}
              {isPaused && (
                <section className="flex flex-col gap-2">
                  <div className="text-xs font-semibold uppercase tracking-wide text-[var(--sentiment-warning)]">
                    Edit Agent (Paused)
                  </div>
                  <div className="rounded-lg bg-[var(--background)] border border-[var(--sentiment-warning)]/40 p-3 flex flex-col gap-4">
                    {/* Personality sliders */}
                    <div>
                      <p className="text-[11px] font-medium text-[var(--muted-foreground)] mb-2">
                        Personality
                      </p>
                      <div className="flex flex-col gap-2">
                        {PERSONALITY_KEYS.map((key) => (
                          <EditSlider
                            key={key}
                            label={key}
                            value={editPersonality[key] ?? 0}
                            onChange={(v) =>
                              setEditPersonality((prev) => ({ ...prev, [key]: v }))
                            }
                          />
                        ))}
                      </div>
                    </div>

                    {/* Emotion sliders */}
                    <div>
                      <p className="text-[11px] font-medium text-[var(--muted-foreground)] mb-2">
                        Emotion
                      </p>
                      <div className="flex flex-col gap-2">
                        {Object.keys(agent.emotion ?? {}).map((key) => (
                          <EditSlider
                            key={key}
                            label={key}
                            value={editEmotion[key] ?? 0}
                            onChange={(v) =>
                              setEditEmotion((prev) => ({ ...prev, [key]: v }))
                            }
                          />
                        ))}
                      </div>
                    </div>

                    {/* Belief slider */}
                    <div>
                      <p className="text-[11px] font-medium text-[var(--muted-foreground)] mb-2">
                        Belief (−1 to +1)
                      </p>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-[var(--muted-foreground)]">−1</span>
                        <input
                          type="range"
                          min={-1}
                          max={1}
                          step={0.01}
                          value={editBelief}
                          onChange={(e) => setEditBelief(parseFloat(e.target.value))}
                          className="flex-1 accent-[var(--primary)] h-2 cursor-pointer"
                        />
                        <span className="text-[11px] text-[var(--muted-foreground)]">+1</span>
                        <span className="w-12 text-right text-[11px] font-mono text-[var(--foreground)]">
                          {editBelief.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="h-8 px-4 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
                    >
                      {saving ? "Saving..." : "Apply Changes"}
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>
    </>
  );
}

function InfoRow({
  label,
  value,
  mono,
  valueClass,
}: {
  label: string;
  value: string;
  mono?: boolean;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] text-[var(--muted-foreground)] shrink-0">{label}</span>
      <span
        className={`text-[11px] truncate text-right ${mono ? "font-mono" : ""} ${valueClass ?? "text-[var(--foreground)]"}`}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}
