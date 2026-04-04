"""F26 API/Integration Hooks — external data injection into a running simulation.
SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from uuid import UUID, uuid4

from app.engine.agent.perception import EnvironmentEvent
from app.engine.agent.schema import (
    AgentAction,
    AgentEmotion,
    AgentPersonality,
    AgentState,
    AgentType,
)
from app.engine.simulation.orchestrator import SimulationOrchestrator

logger = logging.getLogger(__name__)


class ExternalDataHook:
    """Inject external data into simulation at runtime.
    SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks
    """

    def __init__(self, orchestrator: SimulationOrchestrator) -> None:
        self._orchestrator = orchestrator
        # stream_config[simulation_id] = {provider, stream_url}
        self._stream_configs: dict[UUID, dict] = {}

    # ------------------------------------------------------------------ #
    # inject_agents
    # ------------------------------------------------------------------ #

    def inject_agents(
        self,
        simulation_id: UUID,
        agent_configs: list[dict],
    ) -> list[UUID]:
        """Add new agents mid-simulation. Returns new agent IDs.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks

        Each entry in *agent_configs* may contain the following optional keys:
          - agent_type (str):  "consumer" | "influencer" | "expert"
          - community_id (str | UUID): community the agent belongs to
          - belief (float): initial belief in [-1.0, 1.0]
          - personality (dict): keys matching AgentPersonality fields
          - emotion (dict): keys matching AgentEmotion fields

        Returns:
            List of newly created agent UUIDs in the same order as the input.

        Raises:
            ValueError: if simulation_id is unknown.
        """
        state = self._orchestrator.get_state(simulation_id)
        new_ids: list[UUID] = []

        for cfg in agent_configs:
            agent_id = uuid4()

            # Agent type
            agent_type_str = cfg.get("agent_type", "consumer")
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                agent_type = AgentType.CONSUMER

            # Community
            raw_community = cfg.get("community_id")
            if raw_community is not None:
                community_id = (
                    UUID(str(raw_community))
                    if not isinstance(raw_community, UUID)
                    else raw_community
                )
            elif state.agents:
                # Default: same community as the first existing agent
                community_id = state.agents[0].community_id
            else:
                community_id = uuid4()

            # Personality
            personality_data = cfg.get("personality", {})
            personality = AgentPersonality(
                openness=float(personality_data.get("openness", 0.5)),
                skepticism=float(personality_data.get("skepticism", 0.3)),
                trend_following=float(personality_data.get("trend_following", 0.5)),
                brand_loyalty=float(personality_data.get("brand_loyalty", 0.4)),
                social_influence=float(personality_data.get("social_influence", 0.4)),
            )

            # Emotion
            emotion_data = cfg.get("emotion", {})
            emotion = AgentEmotion(
                interest=float(emotion_data.get("interest", 0.5)),
                trust=float(emotion_data.get("trust", 0.5)),
                skepticism=float(emotion_data.get("skepticism", 0.3)),
                excitement=float(emotion_data.get("excitement", 0.3)),
            )

            agent = AgentState(
                agent_id=agent_id,
                simulation_id=simulation_id,
                agent_type=agent_type,
                step=state.current_step,
                personality=personality,
                emotion=emotion,
                belief=float(cfg.get("belief", 0.0)),
                action=AgentAction.IGNORE,
                exposure_count=0,
                adopted=False,
                community_id=community_id,
                influence_score=float(cfg.get("influence_score", 0.0)),
                llm_tier_used=None,
            )
            state.agents.append(agent)
            new_ids.append(agent_id)
            logger.debug("Injected agent %s into simulation %s", agent_id, simulation_id)

        return new_ids

    # ------------------------------------------------------------------ #
    # inject_network_edges
    # ------------------------------------------------------------------ #

    def inject_network_edges(
        self,
        simulation_id: UUID,
        edges: list[tuple[UUID, UUID, float]],
    ) -> int:
        """Add edges between existing agents. Returns count added.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks

        Args:
            simulation_id: target simulation.
            edges: list of (source_agent_id, target_agent_id, weight) tuples.
                   The weight must be in [0.0, 1.0]. Duplicate edges are
                   silently skipped (existing edge is kept).

        Returns:
            Number of edges actually added to the graph.

        Raises:
            ValueError: if simulation_id is unknown or network graph is None.
        """
        state = self._orchestrator.get_state(simulation_id)
        if state.network is None or state.network.graph is None:
            raise ValueError(
                f"Simulation {simulation_id} has no network graph; "
                "cannot inject edges."
            )

        graph = state.network.graph
        added = 0
        for src, dst, weight in edges:
            src_str = str(src)
            dst_str = str(dst)
            if not graph.has_edge(src_str, dst_str):
                graph.add_edge(src_str, dst_str, weight=float(weight))
                added += 1
                logger.debug(
                    "Injected edge %s -> %s (weight=%.3f) into simulation %s",
                    src_str, dst_str, weight, simulation_id,
                )
            else:
                logger.debug(
                    "Edge %s -> %s already exists; skipping.", src_str, dst_str
                )

        return added

    # ------------------------------------------------------------------ #
    # inject_external_signal
    # ------------------------------------------------------------------ #

    def inject_external_signal(
        self,
        simulation_id: UUID,
        signal: dict,
    ) -> None:
        """Inject an external signal (e.g., real-world event data) into the simulation.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks

        The signal dict is converted to an EnvironmentEvent and appended to
        ``state.injected_events`` so that the next simulation step processes it.

        Expected signal keys:
          - event_type (str): one of the EnvironmentEvent literal types.
            Defaults to ``"community_discussion"`` if unrecognised.
          - message (str): content of the signal.
          - source_agent_id (str | UUID | None): originating agent, if any.
          - channel (str): distribution channel (default ``"external"``).
          - content_id (str | UUID | None): optional content identifier.

        Raises:
            ValueError: if simulation_id is unknown.
        """
        state = self._orchestrator.get_state(simulation_id)

        _VALID_EVENT_TYPES = frozenset({
            "campaign_ad", "influencer_post", "expert_review",
            "community_discussion",
        })

        raw_event_type = signal.get("event_type", "community_discussion")
        event_type = (
            raw_event_type if raw_event_type in _VALID_EVENT_TYPES
            else "community_discussion"
        )

        raw_content_id = signal.get("content_id")
        content_id = (
            UUID(str(raw_content_id)) if raw_content_id is not None else uuid4()
        )

        raw_source = signal.get("source_agent_id")
        source_agent_id: UUID | None = (
            UUID(str(raw_source)) if raw_source is not None else None
        )

        env_event = EnvironmentEvent(
            event_type=event_type,  # type: ignore[arg-type]
            content_id=content_id,
            message=str(signal.get("message", "")),
            source_agent_id=source_agent_id,
            channel=str(signal.get("channel", "external")),
            timestamp=state.current_step,
        )
        state.injected_events.append(env_event)
        logger.debug(
            "Injected external signal (type=%s) into simulation %s",
            event_type, simulation_id,
        )

    # ------------------------------------------------------------------ #
    # connect_llm_stream
    # ------------------------------------------------------------------ #

    def connect_llm_stream(
        self,
        simulation_id: UUID,
        provider: str,
        stream_url: str,
    ) -> None:
        """Connect an external LLM stream for real-time cognition.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks

        This is a placeholder for future streaming LLM integration. The
        connection configuration is stored and can be retrieved via
        ``get_stream_config()``.  No actual network connection is made.

        Raises:
            ValueError: if simulation_id is unknown.
        """
        # Validate simulation exists
        self._orchestrator.get_state(simulation_id)

        self._stream_configs[simulation_id] = {
            "provider": provider,
            "stream_url": stream_url,
        }
        logger.info(
            "LLM stream config stored for simulation %s (provider=%s, url=%s)",
            simulation_id, provider, stream_url,
        )

    def get_stream_config(self, simulation_id: UUID) -> dict | None:
        """Return stored LLM stream config, or None if not set.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks
        """
        return self._stream_configs.get(simulation_id)

    # ------------------------------------------------------------------ #
    # export_state_snapshot
    # ------------------------------------------------------------------ #

    def export_state_snapshot(self, simulation_id: UUID) -> dict:
        """Export complete simulation state as a serializable dict.

        SPEC: docs/spec/09_HARNESS_SPEC.md#f26-apiintegration-hooks

        Returns a dict with keys:
          - simulation_id (str)
          - status (str)
          - current_step (int)
          - agent_count (int)
          - agents (list[dict])
          - network (dict): node_count, edge_count, edges
          - config (dict)
          - step_history (list[dict])
          - injected_events (list[dict])

        Raises:
            ValueError: if simulation_id is unknown.
        """
        state = self._orchestrator.get_state(simulation_id)

        # Serialize agents
        agents_data: list[dict] = []
        for agent in state.agents:
            agents_data.append({
                "agent_id": str(agent.agent_id),
                "simulation_id": str(agent.simulation_id),
                "agent_type": agent.agent_type.value,
                "step": agent.step,
                "belief": agent.belief,
                "action": agent.action.value,
                "exposure_count": agent.exposure_count,
                "adopted": agent.adopted,
                "community_id": str(agent.community_id),
                "influence_score": agent.influence_score,
                "llm_tier_used": agent.llm_tier_used,
                "personality": asdict(agent.personality),
                "emotion": asdict(agent.emotion),
                "activity_vector": agent.activity_vector,
            })

        # Serialize network
        network_data: dict = {}
        if state.network is not None and state.network.graph is not None:
            graph = state.network.graph
            network_data = {
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
                "edges": [
                    {
                        "source": str(u),
                        "target": str(v),
                        "weight": float(d.get("weight", 1.0)),
                    }
                    for u, v, d in graph.edges(data=True)
                ],
            }

        # Serialize step_history (StepResult dataclasses)
        step_history_data: list[dict] = []
        for step_result in state.step_history:
            try:
                step_history_data.append(asdict(step_result))
            except TypeError:
                # Fallback if not a dataclass
                step_history_data.append({"step": getattr(step_result, "step", None)})

        # Serialize injected_events
        injected_events_data: list[dict] = [
            {
                "event_type": ev.event_type,
                "content_id": str(ev.content_id),
                "message": ev.message,
                "source_agent_id": str(ev.source_agent_id) if ev.source_agent_id else None,
                "channel": ev.channel,
                "timestamp": ev.timestamp,
            }
            for ev in state.injected_events
        ]

        # Serialize config (dataclass → dict via asdict)
        try:
            config_data = asdict(state.config)
            # Convert UUID fields to strings for JSON-safety
            config_data["simulation_id"] = str(state.config.simulation_id)
        except TypeError:
            config_data = {}

        return {
            "simulation_id": str(simulation_id),
            "status": state.status,
            "current_step": state.current_step,
            "agent_count": len(state.agents),
            "agents": agents_data,
            "network": network_data,
            "config": config_data,
            "step_history": step_history_data,
            "injected_events": injected_events_data,
        }
