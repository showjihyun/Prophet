/**
 * Auto-step interval loop for the Simulation Control Bar.
 * Runs sim.step() repeatedly while status === RUNNING, respecting the
 * current `speed` setting. Skips when runAll is active (server handles steps).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import { useEffect, useRef, type MutableRefObject } from "react";
import { apiClient } from "../../../api/client";
import { useSimulationStore } from "../../../store/simulationStore";
import { SIM_STATUS } from "@/config/constants";

export function useAutoStepLoop(
  runAllLoading: boolean,
  runAllLoadingRef: MutableRefObject<boolean>,
) {
  const status = useSimulationStore((s) => s.status);
  const speed = useSimulationStore((s) => s.speed);
  const simulation = useSimulationStore((s) => s.simulation);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const setStatus = useSimulationStore((s) => s.setStatus);

  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // FE-PERF-10: prevent request pileup at high speeds (in-flight guard)
  const stepInFlightRef = useRef(false);

  // Stable refs for simulation ID and max_steps — updated on every render so
  // the interval callback sees current values without being a dependency.
  const simIdRef = useRef(simulation?.simulation_id);
  const maxStepsRef = useRef(simulation?.max_steps ?? 365);
  useEffect(() => {
    simIdRef.current = simulation?.simulation_id;
    maxStepsRef.current = simulation?.max_steps ?? 365;
  });

  useEffect(() => {
    if (status !== SIM_STATUS.RUNNING || !simIdRef.current || runAllLoading) {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
      return;
    }

    const runStep = async () => {
      const simId = simIdRef.current;
      if (!simId) return;
      // Ref check catches the one-render gap where status is RUNNING
      // but the React state `runAllLoading` hasn't propagated yet.
      if (runAllLoadingRef.current) return;
      if (stepInFlightRef.current) return;
      stepInFlightRef.current = true;
      try {
        const result = await apiClient.simulations.step(simId);
        appendStep(result);
        if (result.step + 1 >= maxStepsRef.current) {
          setStatus(SIM_STATUS.COMPLETED);
        }
      } catch {
        setStatus(SIM_STATUS.PAUSED);
      } finally {
        stepInFlightRef.current = false;
      }
    };

    stepIntervalRef.current = setInterval(runStep, 1000 / speed);
    return () => {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
    };
  }, [status, speed, appendStep, setStatus, runAllLoading, runAllLoadingRef]);
}
