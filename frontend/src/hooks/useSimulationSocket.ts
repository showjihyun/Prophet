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
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!simulationId) return;

    let retryCount = 0;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const ws = new WebSocket(`${WS_BASE}/ws/${simulationId}`);
      wsRef.current = ws;

      let heartbeatInterval: ReturnType<typeof setInterval>;

      ws.onopen = () => {
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
      clearTimeout(retryTimeout);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [simulationId]);

  const send = useCallback((message: unknown) => {
    wsRef.current?.send(JSON.stringify(message));
  }, []);

  const reconnect = useCallback(() => {
    if (!simulationId) return;
    setRetryExhausted(false);
    wsRef.current?.close();
    wsRef.current = null;
    // The useEffect will re-trigger on simulationId change;
    // for manual reconnect, we force a fresh connection via state reset.
  }, [simulationId]);

  return { connected, lastMessage, send, retryExhausted, reconnect };
}
