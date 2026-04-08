/**
 * Shared state for the "Load Previous" and "Compare" dropdowns on the
 * Simulation Control Bar. Holds the list of previous simulations, the
 * open/search state for the Load dropdown, and loader callbacks.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../../api/client";
import { useSimulationStore } from "../../../store/simulationStore";
import type { SimulationRun } from "../../../types/simulation";

export function usePrevSimulations() {
  const navigate = useNavigate();

  const [prevSimulations, setPrevSimulations] = useState<SimulationRun[]>([]);
  const [prevSimOpen, setPrevSimOpen] = useState(false);
  const [prevSimSearch, setPrevSimSearch] = useState("");

  const filteredPrevSimulations = useMemo(() => {
    if (!prevSimSearch.trim()) return prevSimulations.slice(0, 20);
    const q = prevSimSearch.toLowerCase();
    return prevSimulations
      .filter((s) => s.name.toLowerCase().includes(q) || s.simulation_id.includes(q))
      .slice(0, 20);
  }, [prevSimulations, prevSimSearch]);

  const ensureLoaded = async () => {
    if (prevSimulations.length > 0) return;
    try {
      const res = await apiClient.simulations.list();
      setPrevSimulations(res.items ?? []);
    } catch { /* ignore */ }
  };

  const handleOpenPrevSimulations = async () => {
    setPrevSimOpen((open) => !open);
    await ensureLoaded();
  };

  const handleLoadPrevSimulation = async (simId: string) => {
    setPrevSimOpen(false);
    try {
      const sim = await apiClient.simulations.get(simId);
      useSimulationStore.getState().setSimulation(sim);
      const stepsData = await apiClient.simulations.getSteps(simId);
      // FE-PERF-03: single bulk update instead of O(n^2) per-step loop
      useSimulationStore.getState().setStepsBulk(stepsData);
      navigate(`/simulation/${simId}`);
    } catch { /* ignore */ }
  };

  return {
    prevSimulations,
    prevSimOpen,
    setPrevSimOpen,
    prevSimSearch,
    setPrevSimSearch,
    filteredPrevSimulations,
    ensureLoaded,
    handleOpenPrevSimulations,
    handleLoadPrevSimulation,
  };
}
