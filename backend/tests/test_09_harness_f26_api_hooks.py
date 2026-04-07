"""
Auto-generated from SPEC: docs/spec/09_HARNESS_SPEC.md
SPEC Version: 0.1.0
Covers: F26 ExternalDataHook — API/Integration Hooks
"""
from __future__ import annotations

from uuid import uuid4, UUID

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_orchestrator_with_sim():
    """Create a SimulationOrchestrator with a single configured simulation."""
    from app.engine.simulation.orchestrator import SimulationOrchestrator
    from app.engine.simulation.schema import (
        CampaignConfig,
        CommunityConfig,
        SimulationConfig,
    )
    from app.engine.network.schema import NetworkConfig

    orch = SimulationOrchestrator()
    config = SimulationConfig(
        name="F26 Test Simulation",
        communities=[
            CommunityConfig(
                id="f26_community",
                name="F26 Community",
                size=10,
                agent_type="consumer",
                personality_profile={
                    "openness": 0.5,
                    "skepticism": 0.3,
                    "trend_following": 0.5,
                    "brand_loyalty": 0.4,
                    "social_influence": 0.4,
                },
            )
        ],
        campaign=CampaignConfig(
            name="F26 Campaign",
            budget=100.0,
            channels=["sns"],
            message="F26 test",
        ),
        network_config=NetworkConfig(),
        random_seed=42,
    )
    state = orch.create_simulation(config)
    return orch, state.simulation_id


# ---------------------------------------------------------------------------
# F26 — ExternalDataHook
# ---------------------------------------------------------------------------

@pytest.mark.phase2
@pytest.mark.unit
class TestExternalDataHookImport:
    """Smoke: ExternalDataHook is importable."""

    def test_import(self):
        from harness.api_hooks import ExternalDataHook  # noqa: F401

    def test_instantiation(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        assert hook is not None


@pytest.mark.phase2
@pytest.mark.unit
class TestInjectAgents:
    """SPEC: 09_HARNESS_SPEC.md#f26 — inject_agents"""

    def test_returns_list_of_uuids(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        new_ids = hook.inject_agents(sim_id, [{}])
        assert isinstance(new_ids, list)
        assert len(new_ids) == 1
        assert isinstance(new_ids[0], UUID)

    def test_agents_appended_to_state(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        before_count = len(state.agents)
        hook = ExternalDataHook(orch)
        hook.inject_agents(sim_id, [{}, {}])
        assert len(state.agents) == before_count + 2

    def test_inject_multiple_returns_same_count(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        configs = [{"agent_type": "consumer"} for _ in range(5)]
        new_ids = hook.inject_agents(sim_id, configs)
        assert len(new_ids) == 5

    def test_custom_personality_applied(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        cfg = {"personality": {"openness": 0.9, "skepticism": 0.1,
                               "trend_following": 0.8, "brand_loyalty": 0.7,
                               "social_influence": 0.6}}
        new_ids = hook.inject_agents(sim_id, [cfg])
        state = orch.get_state(sim_id)
        new_agent = next(a for a in state.agents if a.agent_id == new_ids[0])
        assert abs(new_agent.personality.openness - 0.9) < 1e-9

    def test_custom_belief_applied(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        new_ids = hook.inject_agents(sim_id, [{"belief": 0.75}])
        state = orch.get_state(sim_id)
        new_agent = next(a for a in state.agents if a.agent_id == new_ids[0])
        assert abs(new_agent.belief - 0.75) < 1e-9

    def test_invalid_simulation_raises(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        with pytest.raises((ValueError, KeyError)):
            hook.inject_agents(uuid4(), [{}])

    def test_simulation_id_assigned_to_new_agent(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        new_ids = hook.inject_agents(sim_id, [{}])
        state = orch.get_state(sim_id)
        new_agent = next(a for a in state.agents if a.agent_id == new_ids[0])
        assert new_agent.simulation_id == sim_id


@pytest.mark.phase2
@pytest.mark.unit
class TestInjectNetworkEdges:
    """SPEC: 09_HARNESS_SPEC.md#f26 — inject_network_edges"""

    def test_returns_count_added(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        # Inject brand-new UUID nodes — guaranteed not to collide
        count = hook.inject_network_edges(
            sim_id,
            [(uuid4(), uuid4(), 0.5)],
        )
        assert isinstance(count, int)
        assert count >= 0

    def test_new_edge_appears_in_graph(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        src = uuid4()
        dst = uuid4()
        count = hook.inject_network_edges(sim_id, [(src, dst, 0.6)])
        assert count == 1
        assert state.network.graph.has_edge(str(src), str(dst))

    def test_duplicate_edge_not_added(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        src, dst = uuid4(), uuid4()
        # First injection
        hook.inject_network_edges(sim_id, [(src, dst, 0.5)])
        # Second injection — same edge, should not be added again
        count = hook.inject_network_edges(sim_id, [(src, dst, 0.5)])
        assert count == 0

    def test_edge_weight_stored_correctly(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        src, dst = uuid4(), uuid4()
        hook.inject_network_edges(sim_id, [(src, dst, 0.42)])
        state = orch.get_state(sim_id)
        edge_data = state.network.graph[str(src)][str(dst)]
        assert abs(edge_data["weight"] - 0.42) < 1e-9

    def test_invalid_simulation_raises(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        with pytest.raises((ValueError, KeyError)):
            hook.inject_network_edges(uuid4(), [(uuid4(), uuid4(), 0.5)])


@pytest.mark.phase2
@pytest.mark.unit
class TestInjectExternalSignal:
    """SPEC: 09_HARNESS_SPEC.md#f26 — inject_external_signal"""

    def test_signal_added_to_injected_events(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        before_count = len(state.injected_events)
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(sim_id, {"message": "Real-world news"})
        assert len(state.injected_events) == before_count + 1

    def test_event_type_preserved_when_valid(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(
            sim_id,
            {"event_type": "influencer_post", "message": "big announcement"},
        )
        last_event = state.injected_events[-1]
        assert last_event.event_type == "influencer_post"

    def test_unknown_event_type_defaults_to_community_discussion(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(
            sim_id,
            {"event_type": "totally_unknown_type", "message": "hello"},
        )
        last_event = state.injected_events[-1]
        assert last_event.event_type == "community_discussion"

    def test_message_stored_on_event(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(sim_id, {"message": "breaking signal"})
        assert state.injected_events[-1].message == "breaking signal"

    def test_channel_defaults_to_external(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(sim_id, {})
        assert state.injected_events[-1].channel == "external"

    def test_invalid_simulation_raises(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        with pytest.raises((ValueError, KeyError)):
            hook.inject_external_signal(uuid4(), {"message": "oops"})


@pytest.mark.phase2
@pytest.mark.unit
class TestConnectLLMStream:
    """SPEC: 09_HARNESS_SPEC.md#f26 — connect_llm_stream"""

    def test_stream_config_stored(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        hook.connect_llm_stream(sim_id, "anthropic", "https://api.anthropic.com/stream")
        cfg = hook.get_stream_config(sim_id)
        assert cfg is not None
        assert cfg["provider"] == "anthropic"
        assert cfg["stream_url"] == "https://api.anthropic.com/stream"

    def test_stream_config_overwritten_on_reconnect(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        hook.connect_llm_stream(sim_id, "openai", "https://openai.com/v1/stream")
        hook.connect_llm_stream(sim_id, "ollama", "http://localhost:11434/stream")
        cfg = hook.get_stream_config(sim_id)
        assert cfg["provider"] == "ollama"

    def test_no_config_returns_none(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        assert hook.get_stream_config(sim_id) is None

    def test_invalid_simulation_raises(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        with pytest.raises((ValueError, KeyError)):
            hook.connect_llm_stream(uuid4(), "anthropic", "https://example.com")


@pytest.mark.phase2
@pytest.mark.unit
class TestExportStateSnapshot:
    """SPEC: 09_HARNESS_SPEC.md#f26 — export_state_snapshot"""

    def test_returns_dict(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        assert isinstance(snapshot, dict)

    def test_snapshot_has_required_keys(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        for key in ("simulation_id", "status", "current_step", "agent_count",
                    "agents", "network", "config", "step_history",
                    "injected_events"):
            assert key in snapshot, f"Missing key: {key}"

    def test_simulation_id_matches(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        assert snapshot["simulation_id"] == str(sim_id)

    def test_agent_count_matches_state(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        assert snapshot["agent_count"] == len(state.agents)
        assert len(snapshot["agents"]) == len(state.agents)

    def test_agents_are_serializable_dicts(self):
        from harness.api_hooks import ExternalDataHook
        import json
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        # Should not raise
        serialized = json.dumps(snapshot)
        assert len(serialized) > 0

    def test_network_contains_edge_count(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        state = orch.get_state(sim_id)
        hook = ExternalDataHook(orch)
        snapshot = hook.export_state_snapshot(sim_id)
        network = snapshot["network"]
        assert "node_count" in network
        assert "edge_count" in network
        assert network["node_count"] == state.network.graph.number_of_nodes()
        assert network["edge_count"] == state.network.graph.number_of_edges()

    def test_injected_events_reflected_in_snapshot(self):
        from harness.api_hooks import ExternalDataHook
        orch, sim_id = _make_orchestrator_with_sim()
        hook = ExternalDataHook(orch)
        hook.inject_external_signal(sim_id, {"message": "snapshot test event"})
        snapshot = hook.export_state_snapshot(sim_id)
        assert len(snapshot["injected_events"]) >= 1
        messages = [e["message"] for e in snapshot["injected_events"]]
        assert "snapshot test event" in messages

    def test_invalid_simulation_raises(self):
        from harness.api_hooks import ExternalDataHook
        from app.engine.simulation.orchestrator import SimulationOrchestrator
        hook = ExternalDataHook(SimulationOrchestrator())
        with pytest.raises((ValueError, KeyError)):
            hook.export_state_snapshot(uuid4())
