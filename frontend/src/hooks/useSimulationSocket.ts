/**
 * WebSocket hook for real-time simulation updates.
 * @spec docs/spec/07_FRONTEND_SPEC.md#websocket-hook
 */
import { useEffect, useRef, useState, useCallback } from "react";
import { DEFAULT_WS_BASE_URL, WS_MAX_RETRIES, WS_BASE_DELAY_MS, WS_HEARTBEAT_INTERVAL_MS, WS_MAX_RECONNECT_DELAY_MS } from "@/config/constants";

const WS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/^http/, "ws")
  : DEFAULT_WS_BASE_URL;

const MAX_RETRIES = WS_MAX_RETRIES;
const BASE_DELAY = WS_BASE_DELAY_MS;

interface WSMessage {
  type: string;
  data: unknown;
}

export function useSimulationSocket(simulationId: string | null) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [retryExhausted, setRetryExhausted] = useState(false);
  // FE-PERF-11: counter increments on manual reconnect to force effect re-run
  const [reconnectTick, setReconnectTick] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!simulationId) return;

    let retryCount = 0;
    let retryTimeout: ReturnType<typeof setTimeout>;
    // StrictMode / fast-nav guard: after cleanup runs, any in-flight
    // `onclose` must NOT schedule a reconnect. Without this, closing
    // a CONNECTING socket inside cleanup fires `onclose`, which in
    // turn calls `setTimeout(connect, …)` that opens a zombie socket
    // and races with the next effect run.
    let didCancel = false;

    function connect() {
      if (didCancel) return;
      const ws = new WebSocket(`${WS_BASE}/ws/${simulationId}`);
      wsRef.current = ws;

      let heartbeatInterval: ReturnType<typeof setInterval>;

      ws.onopen = () => {
        if (didCancel) { ws.close(); return; }
        setConnected(true);
        setRetryExhausted(false);
        retryCount = 0;
        // Heartbeat ping every 30s to keep connection alive
        heartbeatInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, WS_HEARTBEAT_INTERVAL_MS);
      };

      ws.onclose = () => {
        clearInterval(heartbeatInterval);
        if (didCancel) return;
        setConnected(false);
        if (retryCount < MAX_RETRIES) {
          const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount), WS_MAX_RECONNECT_DELAY_MS);
          retryTimeout = setTimeout(() => {
            retryCount++;
            connect();
          }, delay);
        } else {
          setRetryExhausted(true);
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage;
          if (msg.type === 'pong') return; // skip heartbeat responses
          setLastMessage(msg);
        } catch {
          /* non-JSON message, ignore */
        }
      };
    }

    connect();

    return () => {
      didCancel = true;
      clearTimeout(retryTimeout);
      const ws = wsRef.current;
      if (ws) {
        // Strip listeners so the cleanup's close() doesn't fire onclose
        // → schedule retry → open a zombie socket after unmount.
        // Browser still logs "closed before connection established" for
        // a CONNECTING socket we close here, but that's informational —
        // the retry leak was the real bug.
        ws.onopen = null;
        ws.onclose = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.close();
      }
      wsRef.current = null;
    };
  }, [simulationId, reconnectTick]);

  const send = useCallback((message: unknown) => {
    wsRef.current?.send(JSON.stringify(message));
  }, []);

  const reconnect = useCallback(() => {
    if (!simulationId) return;
    setRetryExhausted(false);
    wsRef.current?.close();
    wsRef.current = null;
    // FE-PERF-11: bump tick → useEffect re-runs and opens a fresh socket
    setReconnectTick((n) => n + 1);
  }, [simulationId]);

  return { connected, lastMessage, send, retryExhausted, reconnect };
}
