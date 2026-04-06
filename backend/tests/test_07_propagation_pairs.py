"""
Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#gap-7
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.

Covers GAP-7: propagation_pairs feature for real-time graph animation.
"""
import pytest
from uuid import uuid4


# ---------------------------------------------------------------------------
# 1. StepResult dataclass — accepts and stores propagation_pairs
# ---------------------------------------------------------------------------

class TestStepResultPropagationPairs:
    """SPEC: docs/spec/04_SIMULATION_SPEC.md#stepresult — propagation_pairs field."""

    def test_stepresult_has_propagation_pairs_field(self):
        """StepResult must expose a propagation_pairs attribute."""
        from app.engine.simulation.schema import StepResult

        result = StepResult(simulation_id=uuid4(), step=0)
        assert hasattr(result, "propagation_pairs")

    def test_stepresult_propagation_pairs_defaults_to_empty_list(self):
        """propagation_pairs must default to an empty list (not None)."""
        from app.engine.simulation.schema import StepResult

        result = StepResult(simulation_id=uuid4(), step=0)
        assert result.propagation_pairs == []
        assert isinstance(result.propagation_pairs, list)

    def test_stepresult_propagation_pairs_stores_dicts(self):
        """propagation_pairs must store and return a list of dicts."""
        from app.engine.simulation.schema import StepResult

        pairs = [
            {"source": str(uuid4()), "target": str(uuid4()), "action": "share", "probability": 0.9},
            {"source": str(uuid4()), "target": str(uuid4()), "action": "like", "probability": 0.5},
        ]
        result = StepResult(simulation_id=uuid4(), step=1, propagation_pairs=pairs)
        assert result.propagation_pairs == pairs
        assert len(result.propagation_pairs) == 2

    def test_stepresult_propagation_pairs_independent_across_instances(self):
        """Each StepResult instance must have its own propagation_pairs list."""
        from app.engine.simulation.schema import StepResult

        r1 = StepResult(simulation_id=uuid4(), step=0)
        r2 = StepResult(simulation_id=uuid4(), step=1)

        r1.propagation_pairs.append({"source": "a", "target": "b", "action": "share", "probability": 0.8})
        assert r2.propagation_pairs == [], "Default list must not be shared between instances"

    def test_stepresult_propagation_pairs_accepts_large_list(self):
        """propagation_pairs must be able to hold up to 50 entries."""
        from app.engine.simulation.schema import StepResult

        pairs = [
            {"source": str(uuid4()), "target": str(uuid4()), "action": "share", "probability": float(i) / 100}
            for i in range(50)
        ]
        result = StepResult(simulation_id=uuid4(), step=2, propagation_pairs=pairs)
        assert len(result.propagation_pairs) == 50


# ---------------------------------------------------------------------------
# 2. StepResultResponse Pydantic model — serializes propagation_pairs correctly
# ---------------------------------------------------------------------------

class TestStepResultResponseSerialization:
    """SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep"""

    def test_stepresultresponse_has_propagation_pairs_field(self):
        """StepResultResponse must expose propagation_pairs."""
        from app.api.schemas import StepResultResponse

        resp = StepResultResponse()
        assert hasattr(resp, "propagation_pairs")

    def test_stepresultresponse_propagation_pairs_defaults_to_empty_list(self):
        """StepResultResponse.propagation_pairs must default to []."""
        from app.api.schemas import StepResultResponse

        resp = StepResultResponse()
        assert resp.propagation_pairs == []

    def test_stepresultresponse_serializes_propagation_pairs(self):
        """model_dump() must include propagation_pairs with correct structure."""
        from app.api.schemas import StepResultResponse

        pairs = [
            {"source": str(uuid4()), "target": str(uuid4()), "action": "share", "probability": 0.85},
        ]
        resp = StepResultResponse(propagation_pairs=pairs)
        dumped = resp.model_dump()

        assert "propagation_pairs" in dumped
        assert len(dumped["propagation_pairs"]) == 1
        pair = dumped["propagation_pairs"][0]
        assert "source" in pair
        assert "target" in pair
        assert "action" in pair
        assert "probability" in pair

    def test_stepresultresponse_serializes_to_json(self):
        """model_dump(mode='json') must produce JSON-safe propagation_pairs."""
        from app.api.schemas import StepResultResponse

        pairs = [
            {"source": str(uuid4()), "target": str(uuid4()), "action": "like", "probability": 0.42},
        ]
        resp = StepResultResponse(propagation_pairs=pairs)
        json_data = resp.model_dump(mode="json")

        assert isinstance(json_data["propagation_pairs"], list)
        assert json_data["propagation_pairs"][0]["probability"] == pytest.approx(0.42)

    def test_stepresultresponse_propagation_pairs_multiple_entries(self):
        """StepResultResponse must handle multiple propagation_pairs entries."""
        from app.api.schemas import StepResultResponse

        pairs = [
            {"source": str(uuid4()), "target": str(uuid4()), "action": "share", "probability": p}
            for p in [0.9, 0.7, 0.5, 0.3, 0.1]
        ]
        resp = StepResultResponse(propagation_pairs=pairs)
        assert len(resp.propagation_pairs) == 5

    def test_stepresultresponse_round_trips_from_dict(self):
        """StepResultResponse must be constructible from a plain dict (API deserialization)."""
        from app.api.schemas import StepResultResponse

        data = {
            "step": 3,
            "adoption_rate": 0.15,
            "propagation_pairs": [
                {"source": str(uuid4()), "target": str(uuid4()), "action": "spread", "probability": 0.6},
            ],
        }
        resp = StepResultResponse(**data)
        assert resp.step == 3
        assert len(resp.propagation_pairs) == 1
        assert resp.propagation_pairs[0]["action"] == "spread"


# ---------------------------------------------------------------------------
# 3. StepRunner._build_propagation_pairs() static method
# ---------------------------------------------------------------------------

class TestBuildPropagationPairs:
    """SPEC: docs/spec/04_SIMULATION_SPEC.md#stepresult — GAP-7 helper."""

    def _make_event(self, probability: float, action_type: str = "share"):
        """Factory: create a PropagationEvent with the given probability."""
        from app.engine.diffusion.schema import PropagationEvent

        return PropagationEvent(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            action_type=action_type,
            probability=probability,
            step=0,
            message_id=uuid4(),
        )

    def test_empty_input_returns_empty_list(self):
        """_build_propagation_pairs([]) must return []."""
        from app.engine.simulation.step_runner import StepRunner

        result = StepRunner._build_propagation_pairs([])
        assert result == []

    def test_returns_list_of_dicts(self):
        """Return value must be a list of dicts."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(0.5)]
        result = StepRunner._build_propagation_pairs(events)

        assert isinstance(result, list)
        assert isinstance(result[0], dict)

    def test_dict_keys_are_source_target_action_probability(self):
        """Each dict must have exactly source, target, action, probability keys."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(0.75, action_type="like")]
        result = StepRunner._build_propagation_pairs(events)

        assert len(result) == 1
        pair = result[0]
        assert set(pair.keys()) == {"source", "target", "action", "probability"}

    def test_source_and_target_are_strings(self):
        """source and target values must be string representations of UUIDs."""
        from app.engine.simulation.step_runner import StepRunner
        from app.engine.diffusion.schema import PropagationEvent

        src_id = uuid4()
        tgt_id = uuid4()
        event = PropagationEvent(
            source_agent_id=src_id,
            target_agent_id=tgt_id,
            action_type="share",
            probability=0.8,
            step=1,
            message_id=uuid4(),
        )
        result = StepRunner._build_propagation_pairs([event])

        assert result[0]["source"] == str(src_id)
        assert result[0]["target"] == str(tgt_id)

    def test_action_is_string(self):
        """action value must be a string."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(0.6, action_type="spread")]
        result = StepRunner._build_propagation_pairs(events)

        assert isinstance(result[0]["action"], str)
        assert result[0]["action"] == "spread"

    def test_probability_is_float(self):
        """probability value must be a float."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(0.65)]
        result = StepRunner._build_propagation_pairs(events)

        assert isinstance(result[0]["probability"], float)
        assert result[0]["probability"] == pytest.approx(0.65)

    def test_sorts_by_probability_descending(self):
        """Output must be sorted by probability descending."""
        from app.engine.simulation.step_runner import StepRunner

        probs = [0.3, 0.9, 0.1, 0.7, 0.5]
        events = [self._make_event(p) for p in probs]
        result = StepRunner._build_propagation_pairs(events)

        returned_probs = [pair["probability"] for pair in result]
        assert returned_probs == sorted(returned_probs, reverse=True)

    def test_sorts_correctly_with_equal_probabilities(self):
        """Events with equal probabilities must all be included and order is stable."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(0.5) for _ in range(5)]
        result = StepRunner._build_propagation_pairs(events)

        assert len(result) == 5
        for pair in result:
            assert pair["probability"] == pytest.approx(0.5)

    def test_limits_to_top_50(self):
        """With more than 50 events, only the top 50 by probability are returned."""
        from app.engine.simulation.step_runner import StepRunner

        # 80 events with distinct probabilities 0.001..0.080
        events = [self._make_event(float(i) / 1000) for i in range(1, 81)]
        result = StepRunner._build_propagation_pairs(events)

        assert len(result) == 50

    def test_limit_returns_highest_probability_events(self):
        """The 50 returned events must be the top-50 by probability."""
        from app.engine.simulation.step_runner import StepRunner

        # 60 events: probabilities 0.01 .. 0.60
        events = [self._make_event(float(i) / 100) for i in range(1, 61)]
        result = StepRunner._build_propagation_pairs(events)

        returned_probs = [pair["probability"] for pair in result]
        # Minimum returned probability must be > 0.10 (only top-50 of 60 kept)
        assert min(returned_probs) == pytest.approx(0.11)
        assert max(returned_probs) == pytest.approx(0.60)

    def test_fewer_than_limit_returns_all(self):
        """With fewer than 50 events, all are returned."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(float(i) / 100) for i in range(1, 21)]  # 20 events
        result = StepRunner._build_propagation_pairs(events)

        assert len(result) == 20

    def test_exactly_50_events_returns_all(self):
        """With exactly 50 events, all 50 are returned."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(float(i) / 100) for i in range(1, 51)]
        result = StepRunner._build_propagation_pairs(events)

        assert len(result) == 50

    def test_custom_limit_parameter(self):
        """_build_propagation_pairs must respect a custom limit argument."""
        from app.engine.simulation.step_runner import StepRunner

        events = [self._make_event(float(i) / 100) for i in range(1, 21)]  # 20 events
        result = StepRunner._build_propagation_pairs(events, limit=5)

        assert len(result) == 5

    def test_with_contextual_packet(self):
        """Events carrying a ContextualPacket must be handled without error."""
        from app.engine.simulation.step_runner import StepRunner
        from app.engine.diffusion.schema import PropagationEvent, ContextualPacket

        packet = ContextualPacket(
            original_content="buy our product",
            sender_emotion_summary="interest=0.9",
            sender_reasoning="good value",
        )
        event = PropagationEvent(
            source_agent_id=uuid4(),
            target_agent_id=uuid4(),
            action_type="share",
            probability=0.88,
            step=0,
            message_id=uuid4(),
            contextual_packet=packet,
        )
        result = StepRunner._build_propagation_pairs([event])

        assert len(result) == 1
        assert result[0]["probability"] == pytest.approx(0.88)

    def test_is_static_method(self):
        """_build_propagation_pairs must be callable without a StepRunner instance."""
        from app.engine.simulation.step_runner import StepRunner

        # Should not raise TypeError even without an instance
        result = StepRunner._build_propagation_pairs([])
        assert result == []
