/**
 * Data fetching hooks using TanStack Query.
 * @spec docs/spec/07_FRONTEND_SPEC.md#data-fetching
 *
 * NOTE: Currently unused. All pages use direct apiClient calls.
 * These hooks are retained for future migration to TanStack Query.
 * When migrating a page, import the relevant hook from here
 * instead of calling apiClient directly.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { SimulationRun } from '../types/simulation';

export function useSimulation(simulationId: string | null) {
  return useQuery({
    queryKey: ['simulation', simulationId],
    queryFn: () => apiClient.simulations.get(simulationId!),
    enabled: !!simulationId,
  });
}

export function useSimulationList() {
  return useQuery({
    queryKey: ['simulations'],
    queryFn: () => apiClient.simulations.list(),
  });
}

export function useStepMutation(simulationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.simulations.step(simulationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulation', simulationId] });
    },
  });
}

export function useNetworkGraph(simulationId: string | null) {
  return useQuery({
    queryKey: ['network', simulationId],
    queryFn: () => apiClient.network.get(simulationId!),
    enabled: !!simulationId,
  });
}

export function useLLMStats(simulationId: string | null) {
  return useQuery({
    queryKey: ['llm-stats', simulationId],
    queryFn: () => apiClient.llm.getStats(simulationId!),
    enabled: !!simulationId,
    refetchInterval: 5000,
  });
}

export function useSimulationRun(simulationId: string | null) {
  return useQuery<SimulationRun>({
    queryKey: ['simulation', simulationId],
    queryFn: () => apiClient.simulations.get(simulationId!),
    enabled: !!simulationId,
  });
}
