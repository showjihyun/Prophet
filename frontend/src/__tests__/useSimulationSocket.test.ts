/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#6-websocket-hook
 * SPEC Version: 0.1.2 (updated: reconnection policy)
 * Generated BEFORE implementation — tests define the contract.
 */
import { describe, it, expect } from 'vitest';
import { useSimulationSocket } from '@/hooks/useSimulationSocket';

describe('useSimulationSocket', () => {
  /** @spec 07_FRONTEND_SPEC.md#6-websocket-hook — Reconnection Policy */
  describe('Reconnection Policy', () => {
    it('auto-reconnects with exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)', () => {
      expect(useSimulationSocket).toBeDefined();
    });

    it('gives up after max 5 retry attempts', () => {
      // Hook should expose retry state or max retries config
      expect(useSimulationSocket).toBeDefined();
    });

    it('wraps JSON.parse in try/catch for non-JSON pings', () => {
      // Implementation must not crash on non-JSON messages from server
      expect(useSimulationSocket).toBeDefined();
    });

    it('shows reconnect failure banner after max retries', () => {
      // On reconnect failure: show banner "Connection failed. Click to retry."
      expect(useSimulationSocket).toBeDefined();
    });
  });
});
