/**
 * WebSocket hook for real-time simulation updates.
 * @spec docs/spec/07_FRONTEND_SPEC.md#websocket-hook
 */
import { useEffect, useRef, useState, useCallback } from "react";

const WS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/^http/, "ws")
  : "ws://localhost:8000";

const MAX_RETRIES = 5;
const BASE_DELAY = 1000;

interface WSMessage {
  type: string;
  data: unknown;
}

export function useSimulationSocket(simulationId: string | null) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!simulationId) return;

    let retryCount = 0;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const ws = new WebSocket(`${WS_BASE}/ws/${simulationId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryCount = 0;
      };

      ws.onclose = () => {
        setConnected(false);
        if (retryCount < MAX_RETRIES) {
          const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount), 30000);
          retryTimeout = setTimeout(() => {
            retryCount++;
            connect();
          }, delay);
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage;
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

  return { connected, lastMessage, send };
}
