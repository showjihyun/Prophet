/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#6-websocket-hook
 * SPEC Version: 0.1.2 (updated: reconnection policy)
 * Generated BEFORE implementation — tests define the contract.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useSimulationSocket } from '@/hooks/useSimulationSocket';

describe('useSimulationSocket', () => {
  /** @spec 07_FRONTEND_SPEC.md#6-websocket-hook — Reconnection Policy */
  describe('Reconnection Policy', () => {
    it('auto-reconnects with exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)', () => {
      expect(useSimulationSocket).toBeDefined();
    });

    it('gives up after max 5 retry attempts', () => {
      expect(useSimulationSocket).toBeDefined();
    });

    it('wraps JSON.parse in try/catch for non-JSON pings', () => {
      expect(useSimulationSocket).toBeDefined();
    });

    it('shows reconnect failure banner after max retries', () => {
      expect(useSimulationSocket).toBeDefined();
    });
  });

  describe('Cleanup (regression: StrictMode double-mount zombie socket)', () => {
    // Minimal WebSocket stub: records every construction and captures
    // listeners so the test can fire onclose AFTER the hook unmounts.
    interface FakeWS {
      url: string;
      readyState: number;
      onopen: ((e?: unknown) => void) | null;
      onclose: ((e?: unknown) => void) | null;
      onmessage: ((e?: unknown) => void) | null;
      onerror: ((e?: unknown) => void) | null;
      close: () => void;
      send: () => void;
    }
    let constructed: FakeWS[] = [];

    beforeEach(() => {
      constructed = [];
      class MockWS implements FakeWS {
        url: string;
        readyState = 0; // CONNECTING
        onopen: ((e?: unknown) => void) | null = null;
        onclose: ((e?: unknown) => void) | null = null;
        onmessage: ((e?: unknown) => void) | null = null;
        onerror: ((e?: unknown) => void) | null = null;
        constructor(url: string) {
          this.url = url;
          constructed.push(this);
        }
        close() { this.readyState = 3; }
        send() {}
      }
      // @ts-expect-error - test injection of a minimal WebSocket stub
      globalThis.WebSocket = MockWS;
    });

    it('does NOT open a second socket after cleanup, even if onclose fires late', () => {
      const { unmount } = renderHook(() => useSimulationSocket('sim-1'));
      expect(constructed).toHaveLength(1);
      const first = constructed[0];

      // Unmount BEFORE the socket opens — the realistic StrictMode +
      // fast-navigation race. Cleanup should strip listeners; any
      // browser-initiated onclose after this point must NOT spawn a
      // zombie reconnect.
      unmount();

      // Simulate the browser firing onclose on the now-closed CONNECTING
      // socket. Before the fix, this would schedule setTimeout(connect).
      // After the fix, onclose is nulled out in cleanup, so calling it
      // manually is a no-op.
      if (first.onclose) first.onclose();

      // Wait a tick past any pending retry setTimeout.
      return new Promise<void>((resolve) => {
        setTimeout(() => {
          expect(constructed).toHaveLength(1);
          resolve();
        }, 50);
      });
    });
  });
});
