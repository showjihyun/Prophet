"""
Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection
SPEC Version: 0.2.0
Generated BEFORE implementation — tests define the contract.
Status: RED (implementation does not exist yet)
"""
import pytest
from uuid import uuid4
from math import ceil


def _make_agents(n_expert=50, n_influencer=100, n_consumer=850):
    from app.engine.agent.schema import (
        AgentState, AgentPersonality, AgentEmotion, AgentType, AgentAction,
    )
    agents = []
    sim_id = uuid4()
    comm_id = uuid4()

    def _make(agent_type, influence, skepticism_e=0.5):
        return AgentState(
            agent_id=uuid4(), simulation_id=sim_id, agent_type=agent_type,
            step=5, personality=AgentPersonality(0.5, 0.5, 0.5, 0.5, 0.5),
            emotion=AgentEmotion(0.5, 0.5, skepticism_e, 0.3), belief=0.0,
            action=AgentAction.IGNORE, exposure_count=0, adopted=False,
            community_id=comm_id, influence_score=influence, llm_tier_used=None,
        )

    for _ in range(n_expert):
        agents.append(_make(AgentType.EXPERT, 0.7))
    for _ in range(n_influencer):
        agents.append(_make(AgentType.INFLUENCER, 0.8))
    for _ in range(n_consumer):
        agents.append(_make(AgentType.CONSUMER, 0.2))
    return agents


@pytest.mark.phase2
class TestTierSelector:
    """SPEC: 01_AGENT_SPEC.md#tier-selection — TierSelector.assign_tiers()"""

    def test_agt10_respects_tier3_cap(self):
        """AGT-10: Tier 3 agents <= ceil(total * max_tier3_ratio)."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        agents = _make_agents()  # 1000 total
        config = TierConfig(max_tier3_ratio=0.10)
        tiers = selector.assign_tiers(agents, config, step_seed=42)
        tier3_count = sum(1 for t in tiers.values() if t == 3)
        assert tier3_count <= ceil(len(agents) * 0.10)

    def test_all_agents_assigned(self):
        """Every agent_id appears exactly once in output."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        agents = _make_agents()
        tiers = selector.assign_tiers(agents, TierConfig(), step_seed=42)
        assert set(tiers.keys()) == {a.agent_id for a in agents}

    def test_experts_prioritized_for_tier3(self):
        """Expert agents should be in Tier 3 (priority 1)."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        from app.engine.agent.schema import AgentType
        selector = TierSelector()
        agents = _make_agents(n_expert=10, n_influencer=10, n_consumer=80)
        config = TierConfig(max_tier3_ratio=0.15)  # 15% of 100 = 15 slots
        tiers = selector.assign_tiers(agents, config, step_seed=42)
        experts = [a for a in agents if a.agent_type == AgentType.EXPERT]
        for expert in experts:
            assert tiers[expert.agent_id] == 3

    def test_empty_agents_raises(self):
        """Empty agent list raises ValueError."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        with pytest.raises(ValueError):
            selector.assign_tiers([], TierConfig(), step_seed=42)

    def test_only_valid_tier_values(self):
        """All tier values must be 1, 2, or 3."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        agents = _make_agents()
        tiers = selector.assign_tiers(agents, TierConfig(), step_seed=42)
        assert all(t in {1, 2, 3} for t in tiers.values())

    def test_deterministic_with_same_seed(self):
        """Same step_seed -> same tier assignments."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        agents = _make_agents()
        config = TierConfig()
        t1 = selector.assign_tiers(agents, config, step_seed=42)
        t2 = selector.assign_tiers(agents, config, step_seed=42)
        assert t1 == t2

    def test_at_least_50_percent_tier1(self):
        """At least 50% of agents must be Tier 1 (config invariant)."""
        from app.engine.agent.tier_selector import TierSelector, TierConfig
        selector = TierSelector()
        agents = _make_agents()
        config = TierConfig(max_tier3_ratio=0.10, max_tier2_ratio=0.10)
        tiers = selector.assign_tiers(agents, config, step_seed=42)
        tier1_count = sum(1 for t in tiers.values() if t == 1)
        assert tier1_count >= len(agents) * 0.5
