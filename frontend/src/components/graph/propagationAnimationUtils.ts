/**
 * GAP-7: Propagation animation utilities for the 3D graph.
 *
 * Exported so that both GraphPanel.tsx and tests can import them directly
 * instead of mirroring magic values.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#gap-7
 */
import { GRAPH_LOD_ZOOM_MID, GRAPH_LOD_ZOOM_FAR } from "@/config/constants";
import type { PropagationPair } from "@/types/simulation";

export type AnimationTier = "closeup" | "midrange" | "overview";

/** Determine animation detail tier based on current zoom level. */
export function getAnimationTier(zoom: number): AnimationTier {
  if (zoom >= GRAPH_LOD_ZOOM_MID) return "closeup";
  if (zoom >= GRAPH_LOD_ZOOM_FAR) return "midrange";
  return "overview";
}

/** Max simultaneous animated propagation pairs per tier.
 *
 * Bumped from the original 50/30/5 after live testing showed the
 * `overview` tier looked dead on real simulations: a typical sim
 * produces 2-10 propagation events per step, the effect samples
 * the top-N by probability, and capping at 5 hid nearly every event.
 * Users read "5 particles across a 5000-edge graph" as "nothing is
 * happening". The new numbers prioritise perceived liveness over
 * raw CPU headroom — particles are cheap relative to the physics
 * solver they ride on top of, and force-graph's InstancedMesh
 * renderer batches them into a single draw call anyway.
 */
export const TIER_LIMITS: Record<AnimationTier, number> = {
  closeup: 100,
  midrange: 60,
  overview: 30,
};

/** Action → particle color mapping. "ignore" is intentionally excluded. */
export const ACTION_COLORS: Record<string, string> = {
  share: "#22c55e",
  comment: "#3b82f6",
  like: "#eab308",
  adopt: "#a855f7",
};

// --------------------------------------------------------------------------- //
// UUID ↔ node_id bridge                                                       //
// --------------------------------------------------------------------------- //
//
// The backend emits `propagation_pairs` with **agent UUIDs** in source/target,
// but the force-graph library identifies links by numeric **graph node_ids**
// ("42", "137"…). Without translating UUID → node_id before populating the
// active-links map, `linkDirectionalParticles.has(key)` silently returns
// false for every edge and NO particles are drawn during a running simulation.
//
// The two functions below are the single source of truth for that bridge.
// Both GraphPanel.tsx and the regression tests import them directly so the
// tests fail loudly if the component drifts from the expected behavior.

/** Minimal node shape — only the fields the bridge touches. */
export interface NodeWithAgentId {
  id: string;
  agent_id?: string;
}

/** Build the agent_id → node_id lookup map from a set of graph nodes. */
export function buildAgentIdToNodeId(
  nodes: readonly NodeWithAgentId[],
): Map<string, string> {
  const m = new Map<string, string>();
  for (const n of nodes) {
    if (n.agent_id) m.set(n.agent_id, n.id);
  }
  return m;
}

/**
 * Translate a batch of propagation pairs into the `activePropLinksRef` map
 * that `linkDirectionalParticles` looks up per-frame.
 *
 * - Filters out actions not in `ACTION_COLORS` (e.g. "ignore", "view").
 * - Skips pairs whose agents are not in the graph (stale messages arriving
 *   before the next graph reload).
 * - Caps at `limit` entries, preserving input order. The caller is
 *   responsible for pre-sorting by relevance (typically probability desc).
 *
 * Returns a Map keyed by `${srcNodeId}__${tgtNodeId}`, which is exactly the
 * key shape `linkParticlesFn` constructs from each force-graph link.
 */
export function buildActivePropLinks(
  pairs: readonly PropagationPair[],
  agentIdToNodeId: ReadonlyMap<string, string>,
  limit: number,
): Map<string, string> {
  const out = new Map<string, string>();
  let remaining = limit;
  for (const p of pairs) {
    if (remaining <= 0) break;
    if (!(p.action in ACTION_COLORS)) continue;
    const srcNode = agentIdToNodeId.get(p.source);
    const tgtNode = agentIdToNodeId.get(p.target);
    if (!srcNode || !tgtNode) continue;
    out.set(`${srcNode}__${tgtNode}`, ACTION_COLORS[p.action] ?? "#94a3b8");
    remaining -= 1;
  }
  return out;
}
