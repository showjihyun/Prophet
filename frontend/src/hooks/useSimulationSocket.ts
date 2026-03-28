/**
 * WebSocket hook for real-time simulation updates.
 * @spec docs/spec/07_FRONTEND_SPEC.md#websocket-hook
 */
import { useEffect, useRef, useState, useCallback } from "react";

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

    const ws = new WebSocket(`ws://localhost:8000/ws/${simulationId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as WSMessage;
      setLastMessage(msg);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [simulationId]);

  const send = useCallback((message: unknown) => {
    wsRef.current?.send(JSON.stringify(message));
  }, []);

  return { connected, lastMessage, send };
}
