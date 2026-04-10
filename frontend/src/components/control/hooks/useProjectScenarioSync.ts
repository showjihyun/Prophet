/**
 * Project/scenario loading + New Simulation/Scenario/Clone handlers for the
 * Simulation Control Bar. Also keeps the Zustand projects list in sync with
 * the TanStack Query cache so navigating into the workspace is instant.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../../api/client";
import { useProjects } from "../../../api/queries";
import { useSimulationStore } from "../../../store/simulationStore";
import { SIM_STATUS } from "@/config/constants";

export function useProjectScenarioSync() {
  const navigate = useNavigate();

  const simulation = useSimulationStore((s) => s.simulation);
  const currentProjectId = useSimulationStore((s) => s.currentProjectId);
  const scenarios = useSimulationStore((s) => s.scenarios);

  const [creating, setCreating] = useState(false);

  // TanStack Query — shared cache with ProjectsListPage. Sync into Zustand so
  // imperative logic elsewhere in ControlPanel keeps reading it from there.
  const projectsQuery = useProjects();
  useEffect(() => {
    if (Array.isArray(projectsQuery.data)) {
      useSimulationStore.getState().setProjects(projectsQuery.data);
    }
  }, [projectsQuery.data]);

  // Auto-restore project from simulation and load scenarios on mount
  useEffect(() => {
    const simProjectId = (simulation as unknown as Record<string, unknown> | undefined)?.project_id as
      | string
      | undefined;
    const effectiveProjectId = currentProjectId || simProjectId;
    if (!effectiveProjectId) return;
    if (!currentProjectId && simProjectId) {
      useSimulationStore.getState().setCurrentProject(simProjectId);
    }
    // Load scenarios whenever the list is empty OR doesn't contain the
    // current simulation (i.e. we need fresh data to find the linked one).
    const haveLinkedScenario = scenarios.some(
      (s) => s.simulation_id === simulation?.simulation_id,
    );
    if (scenarios.length === 0 || (!haveLinkedScenario && simulation)) {
      apiClient.projects
        .get(effectiveProjectId)
        .then((detail) => useSimulationStore.getState().setScenarios(detail.scenarios ?? []))
        .catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProjectId, simulation]);

  // Derive the active scenario id by matching the loaded simulation against
  // the scenarios list. Keeps the scenario dropdown controlled so a direct
  // `/simulation/:id` navigation reflects the right scenario.
  const activeScenarioId = simulation?.simulation_id
    ? scenarios.find((s) => s.simulation_id === simulation.simulation_id)?.scenario_id ?? ""
    : "";

  const handleProjectChange = async (projectId: string) => {
    useSimulationStore.getState().setCurrentProject(projectId || null);
    if (!projectId) {
      useSimulationStore.getState().setScenarios([]);
      return;
    }
    try {
      const detail = await apiClient.projects.get(projectId);
      useSimulationStore.getState().setScenarios(detail.scenarios);
    } catch { /* ignore */ }
  };

  // When the user picks a scenario in the dropdown:
  //  1. If the scenario already has a simulation_id, fetch + load it.
  //  2. Otherwise, auto-create one via POST /projects/{pid}/scenarios/{sid}/run
  //     so the user can press Play immediately.
  const handleScenarioChange = async (scenarioId: string) => {
    const scenario = scenarios.find((s) => s.scenario_id === scenarioId);
    if (!scenario || !currentProjectId) return;

    if (scenario.simulation_id) {
      const simId = scenario.simulation_id;
      try {
        const [sim] = await Promise.all([
          apiClient.simulations.get(simId),
          apiClient.network.getSummary(simId).catch(() => undefined),
        ]);
        useSimulationStore.getState().setSimulation(sim);
      } catch { /* ignore */ }
      return;
    }

    setCreating(true);
    try {
      const { simulation_id: newSimId } = await apiClient.projects.runScenario(
        currentProjectId,
        scenarioId,
      );
      const sim = await apiClient.simulations.get(newSimId);
      useSimulationStore.getState().setSimulation(sim);
      useSimulationStore.getState().setStatus(SIM_STATUS.RUNNING);
      // Read latest scenarios from store to avoid overwriting interleaved updates
      const latest = useSimulationStore.getState().scenarios;
      useSimulationStore.getState().setScenarios(
        latest.map((s) =>
          s.scenario_id === scenarioId
            ? { ...s, simulation_id: newSimId, status: "running" }
            : s,
        ),
      );
    } catch (err) {
      console.error("Failed to auto-run scenario:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleNewScenario = async () => {
    if (!currentProjectId) return;
    const name = window.prompt("New scenario name:");
    if (!name?.trim()) return;
    try {
      const scenario = await apiClient.projects.createScenario(currentProjectId, {
        name: name.trim(),
      });
      const latest = useSimulationStore.getState().scenarios;
      useSimulationStore.getState().setScenarios([...latest, scenario]);
    } catch { /* ignore */ }
  };

  const handleNewSimulation = async () => {
    if (!currentProjectId) {
      alert("Please select a project first.");
      return;
    }
    const name = window.prompt(
      "Simulation name:",
      `Simulation ${new Date().toLocaleDateString()}`,
    );
    if (!name?.trim()) return;
    setCreating(true);
    try {
      const sim = await apiClient.simulations.create({
        name: name.trim(),
        project_id: currentProjectId,
        campaign: {
          name: name.trim(),
          channels: ["social_media"],
          message: "Default campaign message",
          target_communities: [],
        },
        max_steps: 365,
      });
      useSimulationStore.getState().setSimulation(sim);
      useSimulationStore.getState().setStatus(SIM_STATUS.CONFIGURED);
      // Update URL so a page refresh stays on this new sim.
      navigate(`/simulation/${sim.simulation_id}`);
    } catch (err) {
      alert(
        `Failed to create simulation: ${err instanceof Error ? err.message : "Unknown error"}`,
      );
    } finally {
      setCreating(false);
    }
  };

  const handleClone = () => {
    if (!simulation) return;
    useSimulationStore.getState().setCloneConfig({
      name: `${simulation.name} (clone)`,
      campaign: {
        name: `${simulation.name} (clone)`,
        channels: [],
        message: "",
        target_communities: [],
      },
      max_steps: simulation.max_steps,
    });
    navigate("/setup");
  };

  return {
    creating,
    activeScenarioId,
    handleProjectChange,
    handleScenarioChange,
    handleNewScenario,
    handleNewSimulation,
    handleClone,
  };
}
