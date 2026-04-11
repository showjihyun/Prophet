"""WebSocket endpoint for real-time simulation updates.
SPEC: docs/spec/06_API_SPEC.md#7-websocket---wssimulation_id
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)

# ---- Connection manager (Phase 6 in-memory) ----

class ConnectionManager:
    """Manages active WebSocket connections per simulation."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._agent_subscriptions: dict[str, set[str]] = {}  # ws_id -> set of agent_ids
        # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#6.1
        self._seq: dict[str, int] = {}  # sim_id -> monotonic sequence number

    async def connect(self, simulation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(simulation_id, []).append(websocket)
        logger.info("WebSocket connected for simulation %s", simulation_id)

    def disconnect(self, simulation_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(simulation_id, [])
        if websocket in conns:
            conns.remove(websocket)
        ws_id = str(id(websocket))
        self._agent_subscriptions.pop(ws_id, None)
        logger.info("WebSocket disconnected for simulation %s", simulation_id)

    async def broadcast(self, simulation_id: str, message: dict[str, Any]) -> None:
        """Send a message to all connections for a simulation.
        SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#6.1
        """
        # Attach monotonic sequence number for gap detection
        self._seq[simulation_id] = self._seq.get(simulation_id, 0) + 1
        message["seq"] = self._seq[simulation_id]

        conns = self._connections.get(simulation_id, [])
        dead: list[WebSocket] = []
        for ws in list(conns):  # iterate over copy
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in conns:
                conns.remove(ws)

    def subscribe_agent(self, websocket: WebSocket, agent_id: str) -> None:
        ws_id = str(id(websocket))
        self._agent_subscriptions.setdefault(ws_id, set()).add(agent_id)

    def unsubscribe_agent(self, websocket: WebSocket, agent_id: str) -> None:
        ws_id = str(id(websocket))
        subs = self._agent_subscriptions.get(ws_id, set())
        subs.discard(agent_id)

    async def broadcast_agent_updates(
        self,
        simulation_id: str,
        agent_states: dict[str, Any],
    ) -> None:
        """Send agent_update messages to clients subscribed to specific agents.

        SPEC: docs/spec/06_API_SPEC.md#7-websocket---wssimulation_id

        Args:
            agent_states: dict of agent_id -> agent state data
        """
        conns = self._connections.get(simulation_id, [])
        for ws in list(conns):
            ws_id = str(id(ws))
            subscribed = self._agent_subscriptions.get(ws_id, set())
            if not subscribed:
                continue
            for agent_id in subscribed:
                if agent_id in agent_states:
                    try:
                        await ws.send_json({
                            "type": "agent_update",
                            "data": agent_states[agent_id],
                        })
                    except Exception:
                        pass  # dead connection, cleaned up by broadcast


manager = ConnectionManager()


@router.websocket("/ws/{simulation_id}")
async def simulation_ws(websocket: WebSocket, simulation_id: str) -> None:
    """WebSocket endpoint for real-time simulation events.
    SPEC: docs/spec/06_API_SPEC.md#7-websocket---wssimulation_id

    Server -> Client message types:
      - step_result
      - emergent_event
      - status_change
      - agent_update

    Client -> Server message types:
      - pause
      - resume
      - inject_event
      - subscribe_agent
      - unsubscribe_agent
    """
    await manager.connect(simulation_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"detail": "Invalid JSON"},
                })
                continue

            msg_type = msg.get("type")
            data = msg.get("data", {})

            if msg_type == "pause":
                try:
                    from app.api.deps import get_orchestrator
                    orch = get_orchestrator()
                    await orch.pause(UUID(simulation_id))
                    state = orch.get_state(UUID(simulation_id))
                    await manager.broadcast(simulation_id, {
                        "type": "status_change",
                        "data": {"status": "paused", "step": state.current_step},
                    })
                except Exception as exc:
                    logger.warning("WS pause failed for %s: %s", simulation_id, exc)
                    await websocket.send_json({
                        "type": "error",
                        "data": {"detail": f"Pause failed: {exc}"},
                    })

            elif msg_type == "resume":
                try:
                    from app.api.deps import get_orchestrator
                    orch = get_orchestrator()
                    await orch.resume(UUID(simulation_id))
                    state = orch.get_state(UUID(simulation_id))
                    await manager.broadcast(simulation_id, {
                        "type": "status_change",
                        "data": {"status": "running", "step": state.current_step},
                    })
                except Exception as exc:
                    logger.warning("WS resume failed for %s: %s", simulation_id, exc)
                    await websocket.send_json({
                        "type": "error",
                        "data": {"detail": f"Resume failed: {exc}"},
                    })

            elif msg_type == "inject_event":
                try:
                    from app.api.deps import get_orchestrator
                    orch = get_orchestrator()
                    event_type = data.get("event_type", "community_discussion")
                    payload = data.get("payload", {})
                    await orch.inject_event(
                        UUID(simulation_id),
                        event_type=event_type,
                        payload=payload,
                    )
                    state = orch.get_state(UUID(simulation_id))
                    await manager.broadcast(simulation_id, {
                        "type": "status_change",
                        "data": {
                            "status": "event_injected",
                            "event_type": event_type,
                            "step": state.current_step,
                        },
                    })
                except Exception as exc:
                    logger.warning("WS inject_event failed for %s: %s", simulation_id, exc)
                    await websocket.send_json({
                        "type": "error",
                        "data": {"detail": f"Inject failed: {exc}"},
                    })

            elif msg_type == "subscribe_agent":
                agent_id = data.get("agent_id", "")
                manager.subscribe_agent(websocket, agent_id)
                await websocket.send_json({
                    "type": "agent_update",
                    "data": {"agent_id": agent_id, "subscribed": True},
                })

            elif msg_type == "unsubscribe_agent":
                agent_id = data.get("agent_id", "")
                manager.unsubscribe_agent(websocket, agent_id)
                await websocket.send_json({
                    "type": "agent_update",
                    "data": {"agent_id": agent_id, "subscribed": False},
                })

            elif msg_type == "ping":
                # SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#6.2
                import time as _time
                await websocket.send_json({"type": "pong", "ts": _time.time()})

            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"detail": f"Unknown message type: {msg_type}"},
                })

    except WebSocketDisconnect:
        manager.disconnect(simulation_id, websocket)
    except Exception:
        manager.disconnect(simulation_id, websocket)
