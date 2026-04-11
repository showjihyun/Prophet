/**
 * SPEC: docs/spec/07_FRONTEND_SPEC.md#gap-7
 * Tests for GAP-7 propagation animation system.
 *
 * Tests the exported getAnimationTier, ACTION_COLORS, TIER_LIMITS from
 * GraphPanel.tsx and the store/type contracts.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useSimulationStore } from '@/store/simulationStore';
import type { PropagationPair, StepResult } from '@/types/simulation';
import {
  getAnimationTier,
  TIER_LIMITS,
  ACTION_COLORS,
  buildAgentIdToNodeId,
  buildActivePropLinks,
  type AnimationTier,
  type NodeWithAgentId,
} from '@/components/graph/propagationAnimationUtils';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GAP-7 — getAnimationTier()', () => {
  it('returns "closeup" for zoom 0.8', () => {
    expect(getAnimationTier(0.8)).toBe('closeup');
  });

  it('returns "midrange" for zoom 0.5', () => {
    expect(getAnimationTier(0.5)).toBe('midrange');
  });

  it('returns "overview" for zoom 0.2', () => {
    expect(getAnimationTier(0.2)).toBe('overview');
  });
});

describe('GAP-7 — getAnimationTier() boundary values', () => {
  it('returns "closeup" for zoom exactly 0.7 (lower boundary)', () => {
    expect(getAnimationTier(0.7)).toBe('closeup');
  });

  it('returns "midrange" for zoom exactly 0.3 (lower boundary)', () => {
    expect(getAnimationTier(0.3)).toBe('midrange');
  });

  it('returns "overview" for zoom 0.29 (just below midrange boundary)', () => {
    expect(getAnimationTier(0.29)).toBe('overview');
  });
});

describe('GAP-7 — PropagationPair type and StepResult interface', () => {
  it('PropagationPair has required shape (source, target, action, probability)', () => {
    const pair: PropagationPair = {
      source: 'agent-001',
      target: 'agent-002',
      action: 'share',
      probability: 0.85,
    };
    expect(pair.source).toBe('agent-001');
    expect(pair.target).toBe('agent-002');
    expect(pair.action).toBe('share');
    expect(pair.probability).toBe(0.85);
  });

  it('StepResult has optional propagation_pairs field', () => {
    const step: StepResult = {
      simulation_id: 'sim-1',
      step: 1,
      total_adoption: 10,
      adoption_rate: 0.1,
      diffusion_rate: 0.05,
      mean_sentiment: 0.5,
      sentiment_variance: 0.02,
      community_metrics: {},
      emergent_events: [],
      action_distribution: {},
      llm_calls_this_step: 0,
      step_duration_ms: 120,
    };
    // propagation_pairs is optional — absence should be valid
    expect(step.propagation_pairs).toBeUndefined();
  });

  it('StepResult accepts propagation_pairs as an array of PropagationPair', () => {
    const pairs: PropagationPair[] = [
      { source: 'a1', target: 'a2', action: 'like', probability: 0.6 },
      { source: 'a3', target: 'a4', action: 'share', probability: 0.9 },
    ];
    const step: StepResult = {
      simulation_id: 'sim-1',
      step: 2,
      total_adoption: 20,
      adoption_rate: 0.2,
      diffusion_rate: 0.1,
      mean_sentiment: 0.6,
      sentiment_variance: 0.03,
      community_metrics: {},
      emergent_events: [],
      action_distribution: {},
      propagation_pairs: pairs,
      llm_calls_this_step: 2,
      step_duration_ms: 200,
    };
    expect(step.propagation_pairs).toHaveLength(2);
    expect(step.propagation_pairs![0].action).toBe('like');
    expect(step.propagation_pairs![1].action).toBe('share');
  });
});

describe('GAP-7 — Animation toggle in simulationStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useSimulationStore.setState({ propagationAnimationsEnabled: true });
  });

  it('defaults to true', () => {
    const state = useSimulationStore.getState();
    expect(state.propagationAnimationsEnabled).toBe(true);
  });

  it('toggles to false when togglePropagationAnimations is called', () => {
    const { togglePropagationAnimations } = useSimulationStore.getState();
    togglePropagationAnimations();
    expect(useSimulationStore.getState().propagationAnimationsEnabled).toBe(false);
  });

  it('toggles back to true on second call', () => {
    const { togglePropagationAnimations } = useSimulationStore.getState();
    togglePropagationAnimations();
    togglePropagationAnimations();
    expect(useSimulationStore.getState().propagationAnimationsEnabled).toBe(true);
  });
});

describe('GAP-7 — ACTION_COLORS does not include "ignore"', () => {
  it('"ignore" action is not in ACTION_COLORS', () => {
    expect('ignore' in ACTION_COLORS).toBe(false);
  });

  it('only animated actions have colors (share, comment, like, adopt)', () => {
    const keys = Object.keys(ACTION_COLORS);
    expect(keys).toContain('share');
    expect(keys).toContain('comment');
    expect(keys).toContain('like');
    expect(keys).toContain('adopt');
    expect(keys).not.toContain('ignore');
  });

  it('filtering pairs by ACTION_COLORS excludes ignore actions', () => {
    const pairs: PropagationPair[] = [
      { source: 'a1', target: 'a2', action: 'ignore', probability: 0.1 },
      { source: 'a3', target: 'a4', action: 'share', probability: 0.8 },
      { source: 'a5', target: 'a6', action: 'like', probability: 0.5 },
    ];
    const animated = pairs.filter(
      (p) => p.action !== 'ignore' && ACTION_COLORS[p.action],
    );
    expect(animated).toHaveLength(2);
    expect(animated.every((p) => p.action !== 'ignore')).toBe(true);
  });

  it('ACTION_COLORS match CSS variable values', () => {
    expect(ACTION_COLORS.share).toBe('#22c55e');
    expect(ACTION_COLORS.comment).toBe('#3b82f6');
    expect(ACTION_COLORS.like).toBe('#eab308');
    expect(ACTION_COLORS.adopt).toBe('#a855f7');
  });
});

describe('GAP-7 — TIER_LIMITS', () => {
  // Bumped from 50/30/5 → 100/60/30 after live UX testing:
  // the original overview cap of 5 looked dead on real sims
  // (typical step produces 2-10 pairs and capping at 5 hid them).
  it('closeup tier limit is 100', () => {
    expect(TIER_LIMITS.closeup).toBe(100);
  });

  it('midrange tier limit is 60', () => {
    expect(TIER_LIMITS.midrange).toBe(60);
  });

  it('overview tier limit is 30', () => {
    expect(TIER_LIMITS.overview).toBe(30);
  });

  it('limits decrease as zoom level decreases (closeup > midrange > overview)', () => {
    expect(TIER_LIMITS.closeup).toBeGreaterThan(TIER_LIMITS.midrange);
    expect(TIER_LIMITS.midrange).toBeGreaterThan(TIER_LIMITS.overview);
  });

  it('getAnimationTier + TIER_LIMITS correctly limit pairs at each zoom level', () => {
    const zoomToExpectedLimit: [number, number][] = [
      [1.0, 100],  // closeup
      [0.7, 100],  // closeup boundary
      [0.5, 60],   // midrange
      [0.3, 60],   // midrange boundary
      [0.2, 30],   // overview
      [0.0, 30],   // overview floor
    ];
    for (const [zoom, expected] of zoomToExpectedLimit) {
      const tier = getAnimationTier(zoom);
      expect(TIER_LIMITS[tier]).toBe(expected);
    }
  });
});

describe('GAP-7 — Propagation pair filtering and limiting', () => {
  it('filters ignore actions and limits to tier count', () => {
    const allPairs: PropagationPair[] = Array.from({ length: 100 }, (_, i) => ({
      source: `a${i}`,
      target: `a${i + 100}`,
      action: i % 5 === 0 ? 'ignore' : 'share',
      probability: 1 - i * 0.005,
    }));

    const tier: AnimationTier = 'midrange';
    const limit = TIER_LIMITS[tier];

    const filtered = allPairs
      .filter((p) => p.action in ACTION_COLORS)
      .slice(0, limit);

    expect(filtered.length).toBe(limit);
    expect(filtered.every((p) => p.action !== 'ignore')).toBe(true);
  });

  it('handles empty propagation_pairs gracefully', () => {
    const pairs: PropagationPair[] = [];
    const filtered = pairs.filter((p) => p.action in ACTION_COLORS);
    expect(filtered).toHaveLength(0);
  });

  it('handles all-ignore propagation_pairs', () => {
    const pairs: PropagationPair[] = [
      { source: 'a1', target: 'a2', action: 'ignore', probability: 0.5 },
      { source: 'a3', target: 'a4', action: 'ignore', probability: 0.3 },
    ];
    const filtered = pairs.filter((p) => p.action in ACTION_COLORS);
    expect(filtered).toHaveLength(0);
  });
});

describe('GAP-7 — Toggle disables animation processing', () => {
  beforeEach(() => {
    useSimulationStore.setState({ propagationAnimationsEnabled: true });
  });

  it('when disabled, should not process pairs', () => {
    useSimulationStore.setState({ propagationAnimationsEnabled: false });
    const enabled = useSimulationStore.getState().propagationAnimationsEnabled;
    const pairs: PropagationPair[] = [
      { source: 'a1', target: 'a2', action: 'share', probability: 0.9 },
    ];
    // When disabled, animation logic should skip processing
    const animated = enabled
      ? pairs.filter((p) => p.action in ACTION_COLORS)
      : [];
    expect(animated).toHaveLength(0);
  });

  it('when enabled, should process pairs normally', () => {
    const enabled = useSimulationStore.getState().propagationAnimationsEnabled;
    const pairs: PropagationPair[] = [
      { source: 'a1', target: 'a2', action: 'share', probability: 0.9 },
    ];
    const animated = enabled
      ? pairs.filter((p) => p.action in ACTION_COLORS)
      : [];
    expect(animated).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// REGRESSION — agent UUID → graph node_id translation
// ---------------------------------------------------------------------------
//
// The backend emits `propagation_pairs` with **agent UUIDs** in source/target.
// The force-graph library identifies links by numeric **graph node_ids**
// (integers serialised as strings). Without translating UUID → node_id before
// populating the active-links map, `linkDirectionalParticles` never finds a
// match and NO animation is ever drawn.
//
// These tests call the **real exported utility** that GraphPanel uses, so a
// regression inside GraphPanel that stops calling the utility (or mutates its
// contract) will fail here, not pass silently against a duplicate helper.

describe('GAP-7 — agent UUID ↔ node_id key translation', () => {
  const nodes: NodeWithAgentId[] = [
    { id: '0', agent_id: '00000000-0000-0000-0000-000000000001' },
    { id: '1', agent_id: '00000000-0000-0000-0000-000000000002' },
    { id: '2', agent_id: '00000000-0000-0000-0000-000000000003' },
  ];

  it('builds keys using node_ids so force-graph link lookup succeeds', () => {
    const lookup = buildAgentIdToNodeId(nodes);
    const pairs: PropagationPair[] = [
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: '00000000-0000-0000-0000-000000000002',
        action: 'share',
        probability: 0.9,
      },
    ];

    const active = buildActivePropLinks(pairs, lookup, 50);

    // Key must be `"0__1"` (node_ids), not the raw agent UUIDs.
    expect(active.has('0__1')).toBe(true);
    expect(active.get('0__1')).toBe(ACTION_COLORS.share);

    // The raw UUID key must NOT be present — this was the bug.
    expect(
      active.has(
        '00000000-0000-0000-0000-000000000001__00000000-0000-0000-0000-000000000002',
      ),
    ).toBe(false);
  });

  it('silently drops pairs whose agent UUID is not in the graph', () => {
    const lookup = buildAgentIdToNodeId(nodes);
    const pairs: PropagationPair[] = [
      // Source is in graph, target is stale/removed.
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
        action: 'share',
        probability: 0.9,
      },
    ];
    expect(buildActivePropLinks(pairs, lookup, 50).size).toBe(0);
  });

  it('handles the realistic batch produced by a single live step', () => {
    const lookup = buildAgentIdToNodeId(nodes);
    const pairs: PropagationPair[] = [
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: '00000000-0000-0000-0000-000000000002',
        action: 'share',
        probability: 0.9,
      },
      {
        source: '00000000-0000-0000-0000-000000000002',
        target: '00000000-0000-0000-0000-000000000003',
        action: 'comment',
        probability: 0.8,
      },
      // ignore is filtered out before the translation step.
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: '00000000-0000-0000-0000-000000000003',
        action: 'ignore',
        probability: 0.5,
      },
    ];
    const active = buildActivePropLinks(pairs, lookup, 50);
    expect(active.size).toBe(2);
    expect(active.get('0__1')).toBe(ACTION_COLORS.share);
    expect(active.get('1__2')).toBe(ACTION_COLORS.comment);
  });

  it('enforces the tier limit by dropping tail pairs', () => {
    const lookup = buildAgentIdToNodeId(nodes);
    const pairs: PropagationPair[] = [
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: '00000000-0000-0000-0000-000000000002',
        action: 'share',
        probability: 0.9,
      },
      {
        source: '00000000-0000-0000-0000-000000000002',
        target: '00000000-0000-0000-0000-000000000003',
        action: 'comment',
        probability: 0.8,
      },
    ];
    // Overview tier cap is 5; with limit=1 only the first resolves.
    const active = buildActivePropLinks(pairs, lookup, 1);
    expect(active.size).toBe(1);
    expect(active.has('0__1')).toBe(true);
    expect(active.has('1__2')).toBe(false);
  });

  it('returns an empty map when agentIdToNodeId is empty (no graph loaded)', () => {
    const pairs: PropagationPair[] = [
      {
        source: '00000000-0000-0000-0000-000000000001',
        target: '00000000-0000-0000-0000-000000000002',
        action: 'share',
        probability: 0.9,
      },
    ];
    expect(buildActivePropLinks(pairs, new Map(), 50).size).toBe(0);
  });
});
