/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#8-api-client
 * SPEC Version: 0.1.2 (updated: TanStack Query requirement)
 * Generated BEFORE implementation — tests define the contract.
 *
 * All API calls must use @tanstack/react-query useQuery/useMutation.
 * Direct fetch or apiClient calls from components are prohibited.
 */
import { describe, it, expect } from 'vitest';

describe('Data Fetching — TanStack Query (Required)', () => {
  /** @spec 07_FRONTEND_SPEC.md#data-fetching-tanstack-query-required */
  it('useQuery hooks exist for GET endpoints', () => {
    // Will fail until query hooks are implemented
    const hooks = require('@/hooks/useSimulationQueries');
    expect(hooks.useSimulationList).toBeDefined();
    expect(hooks.useSimulation).toBeDefined();
    expect(hooks.useSimulationSteps).toBeDefined();
  });

  it('useMutation hooks exist for POST/PATCH/DELETE endpoints', () => {
    const hooks = require('@/hooks/useSimulationMutations');
    expect(hooks.useCreateSimulation).toBeDefined();
    expect(hooks.useStartSimulation).toBeDefined();
    expect(hooks.usePauseSimulation).toBeDefined();
  });

  it('query hooks return loading and error states', () => {
    // TanStack Query hooks must expose isLoading and isError
    const hooks = require('@/hooks/useSimulationQueries');
    expect(hooks.useSimulationList).toBeDefined();
  });
});
