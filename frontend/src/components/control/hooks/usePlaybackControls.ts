/**
 * Playback handlers (Play/Pause/Step/Reset/RunAll) + keyboard shortcuts for
 * the Simulation Control Bar.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import { useEffect, useRef, useState } from "react";
import { apiClient } from "../../../api/client";
import { useSimulationStore } from "../../../store/simulationStore";
import type { SimulationStatus } from "../../../types/simulation";
import {
  SIM_STATUS,
  TERMINAL_SIM_STATUSES,
  STARTABLE_SIM_STATUSES,
} from "@/config/constants";

export function usePlaybackControls() {
  const status = useSimulationStore((s) => s.status);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const setStatus = useSimulationStore((s) => s.setStatus);

  const [runAllLoading, setRunAllLoading] = useState(false);
  // Ref mirrors runAllLoading so useAutoStepLoop can check synchronously
  // without waiting for a React render cycle (prevents one-render race).
  const runAllLoadingRef = useRef(false);
  const isRunning = status === SIM_STATUS.RUNNING;

  // All handlers read simulation via getState() so keyboard shortcuts
  // always target the current simulation, not a stale closure.
  const getSimId = () => useSimulationStore.getState().simulation?.simulation_id;

  const handlePlay = async () => {
    const simId = getSimId();
    if (!simId) return;
    const recover = async () => {
      await apiClient.simulations.stop(simId).catch(() => undefined);
      await apiClient.simulations.start(simId);
    };
    try {
      if (STARTABLE_SIM_STATUSES.includes(status)) {
        await apiClient.simulations.start(simId);
      } else if (TERMINAL_SIM_STATUSES.includes(status)) {
        await recover();
      } else {
        // Local state says paused/running — try resume, but the backend may
        // have advanced to 'failed' behind our back. On 409 state-mismatch,
        // fall back to full recovery instead of leaving the user stuck.
        try {
          await apiClient.simulations.resume(simId);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          if (msg.includes("409") || msg.toLowerCase().includes("not allowed")) {
            await recover();
          } else {
            throw err;
          }
        }
      }
      setStatus(SIM_STATUS.RUNNING);
    } catch { /* status unchanged on failure */ }
  };

  const handlePause = async () => {
    const simId = getSimId();
    if (!simId) return;
    try {
      await apiClient.simulations.pause(simId);
      setStatus(SIM_STATUS.PAUSED);
    } catch { /* status unchanged */ }
  };

  const handleStep = async () => {
    const simId = getSimId();
    if (!simId) return;
    try {
      const result = await apiClient.simulations.step(simId);
      appendStep(result);
    } catch { /* ignore */ }
  };

  const handleReset = async () => {
    const simId = getSimId();
    if (!simId) return;
    if (!window.confirm("Reset simulation? This will stop the current run.")) return;
    try {
      await apiClient.simulations.stop(simId);
      setStatus(SIM_STATUS.CREATED);
    } catch { /* ignore */ }
  };

  const handleRunAll = async () => {
    const simId = getSimId();
    if (!simId || runAllLoading) return;
    runAllLoadingRef.current = true;
    setRunAllLoading(true);
    setStatus(SIM_STATUS.RUNNING);
    try {
      const report = await apiClient.simulations.runAll(simId);
      setStatus(report.status as SimulationStatus);
    } catch {
      // leave status unchanged on failure
    } finally {
      runAllLoadingRef.current = false;
      setRunAllLoading(false);
    }
  };

  // Keyboard shortcuts: Space=Play/Pause, ArrowRight=Step, Escape=Reset
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      // Skip when a modal/dialog is open — Escape should close the modal, not reset the sim.
      if (document.querySelector("[role='dialog']")) return;
      switch (e.key) {
        case " ":
          e.preventDefault();
          if (isRunning) handlePause(); else handlePlay();
          break;
        case "ArrowRight":
          handleStep();
          break;
        case "Escape":
          handleReset();
          break;
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning]);

  return {
    isRunning,
    runAllLoading,
    runAllLoadingRef,
    handlePlay,
    handlePause,
    handleStep,
    handleReset,
    handleRunAll,
  };
}
