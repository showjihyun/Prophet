/**
 * GraphPanel — 3D AI Social World Graph Engine (Zone 2 Center).
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-panel-3d-rendering
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-center-ai-social-world-graph-engine
 *
 * WebGL / three.js renderer via react-force-graph-3d. Replaces the prior
 * 2D Cytoscape canvas entirely.
 *
 * Controls:
 *   - Left-drag: orbit (rotate around center)
 *   - Scroll:    zoom in / out
 *   - Right-drag: pan
 *
 * Color contract: both nodes AND edges use the community palette from
 * `@/config/constants#COMMUNITIES` (the same palette the left-side
 * Communities legend uses). Intra-community edges take the source node's
 * community color; cross-community/bridge edges fall back to a neutral
 * muted gray so they read as connective tissue, not belonging to either
 * community.
 *
 * Performance contract (1k-5k agents):
 *   - Built-in instanced sphere renderer — NO `nodeThreeObject` callback,
 *     which would create one three.js Mesh per node and stall zoom/pan.
 *     The library batches nodes into a single InstancedMesh draw call.
 *   - `nodeResolution` scales down for large graphs (fewer triangles per
 *     sphere). 2k+ nodes drops to 4 segments.
 *   - `linkDirectionalParticles` disabled entirely when the graph has
 *     more than ~200 edges — particle animation is the biggest per-frame
 *     cost and is pure visual fluff.
 *   - Per-step adoption highlight mutates a ref + calls `refresh()`; the
 *     force simulation does not restart on every simulation step.
 *   - `cooldownTicks` + `d3AlphaDecay` force physics to settle quickly
 *     and stop — once stopped, zoom/pan is pure GPU work.
 *   - `rendererConfig.antialias` is off for large graphs (largest single
 *     win on integrated GPUs).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D, { type ForceGraphMethods } from "react-force-graph-3d";
import { type CytoscapeGraph } from "../../api/client";
import { useNetwork } from "../../api/queries";
import { useSimulationStore } from "../../store/simulationStore";
import { COMMUNITIES } from "@/config/constants";
import type { PropagationPair } from "@/types/simulation";
import {
  getAnimationTier,
  TIER_LIMITS,
  buildAgentIdToNodeId,
  buildActivePropLinks,
  type AnimationTier,
} from "./propagationAnimationUtils";
import GraphLegend from "./GraphLegend";
import ZoomTierBadge from "./ZoomTierBadge";

// --------------------------------------------------------------------------- //
// Types                                                                       //
// --------------------------------------------------------------------------- //

interface GraphNode {
  id: string;
  label: string;
  /** Short community key as returned by the backend (e.g. "M", "S", "A"). */
  community: string;
  /** Human-readable community name from config (e.g. "mainstream"). */
  community_name?: string;
  agent_id?: string;
  agent_type?: string;
  influence_score?: number;
  adopted?: boolean;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  weight?: number;
  edge_type?: string;
  is_bridge?: boolean;
  // Cached at load time so link color is O(1) without chasing the force-graph
  // source/target reference which mutates between string -> node object.
  _srcCommunity?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// --------------------------------------------------------------------------- //
// Community color palette                                                     //
// --------------------------------------------------------------------------- //
//
// The palette is built dynamically from the communities that actually appear
// in the loaded graph, because the backend simulation uses whatever ids the
// user configured (e.g. "M", "E", "S", "I" for mainstream/early_adopters/
// skeptics/influencers). The hardcoded A/B/C/D/E list in `@/config/constants`
// only covered a single default profile and made every real simulation fall
// through to the gray fallback color.
//
// The fallback color palette is used when a community has no entry in the
// static `COMMUNITIES` table. We rotate through it in insertion order so the
// assignment is stable across re-renders of the same graph.

const FALLBACK_COMMUNITY_PALETTE: readonly string[] = [
  "#3b82f6", // blue
  "#22c55e", // green
  "#f97316", // orange
  "#a855f7", // purple
  "#ef4444", // red
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
  "#eab308", // yellow
  "#14b8a6", // teal
];

const STATIC_COMMUNITY_COLOR: Record<string, string> = Object.fromEntries(
  COMMUNITIES.map((c) => [c.id, c.color]),
);

/**
 * Stable palette-slot assignment for communities that have no entry in the
 * static `COMMUNITIES` table. Hashes the community id (not the insertion
 * order) so the same community always picks the same fallback color across
 * graph re-fetches — otherwise pagination, reseeding, or backend node-order
 * changes would flip "mainstream" from blue to orange on refresh.
 */
function fallbackColorFor(communityId: string): string {
  let h = 0;
  for (let i = 0; i < communityId.length; i++) {
    h = (h * 31 + communityId.charCodeAt(i)) | 0;
  }
  return FALLBACK_COMMUNITY_PALETTE[
    Math.abs(h) % FALLBACK_COMMUNITY_PALETTE.length
  ];
}

const DEFAULT_NODE_COLOR = "#64748b";

/**
 * Bright amber used to "flash" agents that actively processed data in
 * the current step (source or target of a propagation pair). Picked
 * for maximum contrast against every community hue in the palette so
 * the highlight reads as "this agent is doing something right now"
 * regardless of which community it belongs to. `#fcd34d` = amber-300,
 * one shade brighter than the previous amber-400 so the strobe phase
 * pops against dark backgrounds.
 */
const ACTIVE_AGENT_GLOW_COLOR = "#fcd34d";

/**
 * Total duration (ms) that an agent strobes after acting. At 150ms
 * per phase (≈6.6 Hz) this gives 10 flashes before the highlight
 * clears and the node settles back to its normal community color.
 * 1.5 s is long enough to catch the eye but short enough that
 * consecutive steps stay visually distinct.
 */
const ACTIVE_AGENT_GLOW_MS = 1_500;

/**
 * Strobe phase length (ms) — how long the "on" state stays visible
 * before flipping to "off". 150 ms ≈ 6.6 Hz, which reads as a clean
 * flash/blink without looking like a glitch. Going below ~100 ms
 * starts to feel like flicker and can cross accessibility thresholds
 * for photosensitive users.
 */
const ACTIVE_AGENT_STROBE_PHASE_MS = 150;

/**
 * Size multiplier for active agents during the "on" strobe phase.
 * The instanced-sphere renderer reads `nodeVal` for each node on
 * every frame, so bumping this is nearly free. 2.2× reads as
 * "noticeably larger" without dominating the scene or colliding
 * with neighbours on dense graphs.
 */
const ACTIVE_AGENT_SIZE_MULTIPLIER = 2.2;

/**
 * Vertical offset applied to the left-side overlays (community legend and
 * the full graph legend) so they don't crowd the middle of the viewport.
 * One constant keeps the two stacked overlays moving together — if you
 * change this, both `top-[calc(50%-…)]` and `bottom-[calc(…)]` styles
 * stay aligned.
 */
const LEFT_LEGEND_OFFSET_PX = 200;
/**
 * Amount (0–1) to blend an adopted node's base community color toward white.
 * Produces a brighter/tinted version of the same hue — preserves community
 * identity while still reading as "converted". 0.35 = ~35% white mix, which
 * lifts saturation enough to pop against the un-adopted base without washing
 * the hue into pastel.
 *
 * This replaces the old single-green `ADOPTED_GLOW_COLOR` (#22c55e). A
 * single global green overrode every community's palette once
 * `adoption_rate` approached 1.0, erasing polarization/faction signal from
 * the 3D view. Tinting per community keeps that signal visible.
 */
const ADOPTED_GLOW_WHITE_MIX = 0.35;
const HIGHLIGHT_DIM_COLOR = "#1e293b";

// Neutral bridge/inter-community edge color. Muted so it reads as connective
// tissue and does not compete with the community hues.
const BRIDGE_EDGE_COLOR = "rgba(148,163,184,0.35)";
const INTER_EDGE_COLOR = "rgba(148,163,184,0.15)";

/**
 * Convert a hex color (`#rrggbb`) to `rgba(r,g,b,alpha)`.
 * Used so intra-community edges reuse the community color at reduced alpha.
 */
function hexToRgba(hex: string, alpha: number): string {
  if (!hex.startsWith("#") || hex.length !== 7) {
    return `rgba(100,116,139,${alpha})`;
  }
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Blend a `#rrggbb` color toward white by `amount` (0–1) and return a new
 * hex string. `amount=0` returns the input unchanged; `amount=1` returns
 * `#ffffff`. Used to derive a per-community "adopted" tint that is visibly
 * brighter than the base community color without hiding its hue.
 */
function brightenHex(hex: string, amount: number): string {
  if (!hex.startsWith("#") || hex.length !== 7) return hex;
  const clamp = Math.max(0, Math.min(1, amount));
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const mix = (c: number) => Math.round(c + (255 - c) * clamp);
  const toHex = (c: number) => c.toString(16).padStart(2, "0");
  return `#${toHex(mix(r))}${toHex(mix(g))}${toHex(mix(b))}`;
}

// --------------------------------------------------------------------------- //
// Data transform: API Cytoscape format -> force-graph format                  //
// --------------------------------------------------------------------------- //

function cytoscapeToForceGraph(api: CytoscapeGraph): GraphData {
  const nodes: GraphNode[] = api.nodes.map((n) => {
    const d = n.data as Record<string, unknown>;
    return {
      id: String(d.id ?? ""),
      label: String(d.label ?? ""),
      community: String(d.community ?? ""),
      community_name: d.community_name as string | undefined,
      agent_id: d.agent_id as string | undefined,
      agent_type: d.agent_type as string | undefined,
      influence_score: d.influence_score as number | undefined,
      adopted: Boolean(d.adopted),
    };
  });

  // Build id -> community lookup so we can stamp each link with its source
  // community once up-front. force-graph mutates `link.source` from a string
  // id into the actual node object later; caching the community avoids
  // branching on that every frame inside the color callback.
  const communityById: Record<string, string> = {};
  for (const n of nodes) communityById[n.id] = n.community;

  const links: GraphLink[] = api.edges.map((e) => {
    const d = e.data as Record<string, unknown>;
    const srcId = String(d.source ?? "");
    return {
      source: srcId,
      target: String(d.target ?? ""),
      weight: d.weight as number | undefined,
      edge_type: d.edge_type as string | undefined,
      is_bridge: Boolean(d.is_bridge),
      _srcCommunity: communityById[srcId],
    };
  });
  return { nodes, links };
}

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

export default function GraphPanel() {
  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [zoomTier, setZoomTier] = useState<AnimationTier>("overview");

  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const latestStep = useSimulationStore((s) => s.latestStep);
  const highlightedCommunity = useSimulationStore((s) => s.highlightedCommunity);
  const setHighlightedCommunity = useSimulationStore((s) => s.setHighlightedCommunity);
  const selectAgent = useSimulationStore((s) => s.selectAgent);
  const propagationAnimEnabled = useSimulationStore((s) => s.propagationAnimationsEnabled);

  // Per-node mutable highlight flags kept off React state to avoid re-renders.
  const adoptedSetRef = useRef<Set<string>>(new Set());

  // GAP-7: Active propagation link set (source→target keys that should show particles)
  const activePropLinksRef = useRef<Map<string, string>>(new Map());
  const propTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Node IDs of agents that actively processed data in the current step
  // (union of propagation_pairs source + target, after UUID→node_id
  // translation). Drives the `ACTIVE_AGENT_GLOW_COLOR` + size boost
  // in the node-render callbacks so the user sees a pulse on every
  // agent that's "doing something right now" — the node-level
  // complement to the edge-level particle effect.
  const activeAgentsRef = useRef<Set<string>>(new Set());
  // Strobe phase — flips true/false every `ACTIVE_AGENT_STROBE_PHASE_MS`
  // while agents are highlighted. Node callbacks only apply the glow
  // color + size boost when this is true, producing the on/off
  // flash/blink effect the user asked for.
  const activeAgentsPhaseRef = useRef<boolean>(false);
  const activeAgentsStrobeRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const activeAgentsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // ---- Load graph data on simulation change ------------------------------- //
  // TanStack Query — cached network graph, instant on revisit
  const networkQuery = useNetwork(simulationId);
  // Derive both `graphData` and `isLoading` directly from the query so we
  // never call setState inside an effect (react-hooks/set-state-in-effect).
  const isLoading = networkQuery.isLoading;
  const graphData = useMemo<GraphData>(() => {
    if (networkQuery.data) {
      return cytoscapeToForceGraph(networkQuery.data as CytoscapeGraph);
    }
    return { nodes: [], links: [] };
  }, [networkQuery.data]);

  // ---- Track container size so the WebGL canvas matches the panel -------- //
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => {
      setDims({ w: el.clientWidth, h: el.clientHeight });
    };
    update();
    // ResizeObserver is guaranteed in all supported browsers (lib.dom).
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ---- Per-step adoption highlight (no graph rebuild) --------------------- //
  useEffect(() => {
    if (!latestStep || graphData.nodes.length === 0) return;
    const adoptionRate = latestStep.adoption_rate ?? 0;
    const total = graphData.nodes.length;
    const adoptCount = Math.floor(total * adoptionRate);

    const sorted = [...graphData.nodes].sort(
      (a, b) => (b.influence_score ?? 0) - (a.influence_score ?? 0),
    );
    const newSet = new Set<string>();
    for (let i = 0; i < adoptCount; i++) newSet.add(sorted[i].id);
    adoptedSetRef.current = newSet;
    fgRef.current?.refresh();
  }, [latestStep, graphData.nodes]);

  // Agent UUID → graph node_id lookup. See the explanation on
  // `buildAgentIdToNodeId` in `propagationAnimationUtils.ts` — this bridge
  // is load-bearing because the backend emits propagation pairs with agent
  // UUIDs while force-graph indexes links by numeric node_ids. Rebuilt only
  // when the graph itself changes.
  const agentIdToNodeId = useMemo(
    () => buildAgentIdToNodeId(graphData.nodes),
    [graphData.nodes],
  );

  // ---- GAP-7: Propagation animation effect -------------------------------- //
  useEffect(() => {
    // Disabling the animation entirely → flush immediately.
    if (!propagationAnimEnabled) {
      activePropLinksRef.current.clear();
      fgRef.current?.refresh();
      return;
    }
    // Step with zero pairs → PRESERVE existing particles. Letting this
    // path clear would cause a visual flash-on/flash-off whenever the
    // backend probability happens to be quiet for a step. The 8s
    // CASCADE_TTL timer below still fades particles naturally.
    if (!latestStep?.propagation_pairs?.length) {
      return;
    }

    // Determine current zoom tier and limit
    const fg = fgRef.current;
    const camera = fg ? (fg as unknown as { camera: () => { position: { length: () => number } } }).camera?.() : null;
    const zoomDist = camera?.position?.length?.() ?? 500;
    // Normalize zoom: closer = higher value (inverse distance, capped at 1.0)
    const normalizedZoom = Math.min(1.0, 300 / Math.max(zoomDist, 1));
    const tier = getAnimationTier(normalizedZoom);
    // Defer setState out of the effect body to avoid the
    // react-hooks/set-state-in-effect rule. The camera is external
    // three.js state that we're synchronising INTO React — the
    // microtask boundary keeps the render cascade linear.
    queueMicrotask(() => setZoomTier(tier));
    const limit = TIER_LIMITS[tier];

    // Delegate filter + UUID→node_id translation + LOD cap to the shared
    // utility. GraphPanel and its regression tests both exercise the same
    // code path, so a behaviour drift here fails loudly in CI.
    const pairs = latestStep.propagation_pairs as PropagationPair[];
    activePropLinksRef.current = buildActivePropLinks(
      pairs,
      agentIdToNodeId,
      limit,
    );

    // Active-agent set — every source and target of a propagation pair
    // is "currently processing data". Used by nodeColorFn / nodeValFn
    // to strobe the node during its glow window.
    const newActiveAgents = new Set<string>();
    for (const p of pairs) {
      const src = agentIdToNodeId.get(p.source);
      const tgt = agentIdToNodeId.get(p.target);
      if (src) newActiveAgents.add(src);
      if (tgt) newActiveAgents.add(tgt);
    }
    // Merge with existing so consecutive steps' active agents visually
    // overlap while the timer counts down.
    for (const id of newActiveAgents) activeAgentsRef.current.add(id);

    fgRef.current?.refresh();

    // Clear particles after CASCADE_TTL_MS (fade out)
    if (propTimerRef.current) clearTimeout(propTimerRef.current);
    propTimerRef.current = setTimeout(() => {
      activePropLinksRef.current.clear();
      fgRef.current?.refresh();
    }, 8_000);

    // Strobe the node highlight on/off at `ACTIVE_AGENT_STROBE_PHASE_MS`
    // intervals for the full `ACTIVE_AGENT_GLOW_MS` window. Each tick
    // flips the phase and asks force-graph to repaint — the
    // instanced-sphere renderer re-reads nodeColor + nodeVal, so the
    // visible change is free after the first flip.
    if (activeAgentsStrobeRef.current) {
      clearInterval(activeAgentsStrobeRef.current);
    }
    // Start the strobe in the "on" phase so the user sees a flash
    // immediately on every new step instead of waiting a cycle.
    activeAgentsPhaseRef.current = true;
    activeAgentsStrobeRef.current = setInterval(() => {
      activeAgentsPhaseRef.current = !activeAgentsPhaseRef.current;
      fgRef.current?.refresh();
    }, ACTIVE_AGENT_STROBE_PHASE_MS);

    // After the full glow window, stop strobing, clear the set, and
    // do one last refresh so the nodes settle back to their community
    // color cleanly.
    if (activeAgentsTimerRef.current) {
      clearTimeout(activeAgentsTimerRef.current);
    }
    activeAgentsTimerRef.current = setTimeout(() => {
      if (activeAgentsStrobeRef.current) {
        clearInterval(activeAgentsStrobeRef.current);
        activeAgentsStrobeRef.current = null;
      }
      activeAgentsRef.current.clear();
      activeAgentsPhaseRef.current = false;
      fgRef.current?.refresh();
    }, ACTIVE_AGENT_GLOW_MS);

    return () => {
      if (propTimerRef.current) clearTimeout(propTimerRef.current);
      if (activeAgentsTimerRef.current) {
        clearTimeout(activeAgentsTimerRef.current);
      }
      if (activeAgentsStrobeRef.current) {
        clearInterval(activeAgentsStrobeRef.current);
      }
    };
  }, [propagationAnimEnabled, latestStep, agentIdToNodeId]);

  // Derive the effective community table from the graph itself — ids, names,
  // colors, counts — so we always reflect whatever the simulation is actually
  // using (not the hardcoded A/B/C/D/E profile). Preserves first-seen order so
  // color assignments stay stable across renders of the same graph.
  //
  // This must live BEFORE the render callbacks below because
  // `nodeColorFn`/`linkColorFn` capture `communityColorMap` in their deps
  // arrays — referencing it before initialization throws a ReferenceError at
  // hook-evaluation time.
  const graphCommunities = useMemo<
    Array<{ id: string; name: string; color: string; count: number }>
  >(() => {
    const order: string[] = [];
    const meta: Record<string, { name: string; count: number }> = {};
    for (const n of graphData.nodes) {
      const id = n.community || "unknown";
      if (!(id in meta)) {
        order.push(id);
        meta[id] = { name: n.community_name ?? id, count: 0 };
      }
      meta[id].count += 1;
      // Upgrade the display name as soon as we see one (first node may be
      // missing it if the backend didn't include community_name).
      if (n.community_name && meta[id].name === id) {
        meta[id].name = n.community_name;
      }
    }
    return order.map((id) => ({
      id,
      name: meta[id].name,
      color: STATIC_COMMUNITY_COLOR[id] ?? fallbackColorFor(id),
      count: meta[id].count,
    }));
  }, [graphData.nodes]);

  // id → color lookup for the render callbacks. Rebuilt only when the
  // community set changes (not on every frame).
  const communityColorMap = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const c of graphCommunities) m[c.id] = c.color;
    return m;
  }, [graphCommunities]);

  // id → "adopted" tint lookup. A brightened version of each community
  // color so adopted agents read as "converted" while keeping their
  // community identity. Precomputed here (not in `nodeColorFn`) so the
  // render callback stays O(1) per node on every frame.
  const adoptedColorMap = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const [id, hex] of Object.entries(communityColorMap)) {
      m[id] = brightenHex(hex, ADOPTED_GLOW_WHITE_MIX);
    }
    return m;
  }, [communityColorMap]);

  // id → display name lookup for hover tooltip and accessibility labels.
  const communityNameMap = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const c of graphCommunities) m[c.id] = c.name;
    return m;
  }, [graphCommunities]);

  // ---- Color + size callbacks (built-in InstancedMesh path) --------------- //
  //
  // Precedence (highest wins):
  //   1. Dimmed (community filter active, not in the highlighted one)
  //   2. Active agent ON-phase (strobing amber + bigger)
  //   3. Adopted (converted) — brightened community tint (per community)
  //   4. Default community color
  //
  // The strobe is realised by consulting `activeAgentsPhaseRef` — it
  // flips true/false every ~150 ms while an agent is in its glow
  // window. During the OFF phase the agent renders with its normal
  // community color and size, which produces the flash/blink feel
  // the user asked for (and which a steady glow could not).
  const nodeColorFn = useCallback(
    (node: object): string => {
      const n = node as GraphNode;
      const dimmed =
        highlightedCommunity !== null && n.community !== highlightedCommunity;
      if (dimmed) return HIGHLIGHT_DIM_COLOR;
      if (
        activeAgentsPhaseRef.current &&
        activeAgentsRef.current.has(n.id)
      ) {
        return ACTIVE_AGENT_GLOW_COLOR;
      }
      if (adoptedSetRef.current.has(n.id)) {
        return (
          adoptedColorMap[n.community] ??
          communityColorMap[n.community] ??
          DEFAULT_NODE_COLOR
        );
      }
      return communityColorMap[n.community] ?? DEFAULT_NODE_COLOR;
    },
    [highlightedCommunity, communityColorMap, adoptedColorMap],
  );

  const nodeValFn = useCallback((node: object): number => {
    const n = node as GraphNode;
    const base = 1 + Math.min(6, (n.influence_score ?? 0.2) * 8.0);
    // Size boost only during the ON phase of the strobe — pairs with
    // the color change in `nodeColorFn` so each flash is both a color
    // AND size change, which reads as a clear "pop" even on dense
    // graphs where a pure color change would be hard to pick out.
    if (activeAgentsPhaseRef.current && activeAgentsRef.current.has(n.id)) {
      return base * ACTIVE_AGENT_SIZE_MULTIPLIER;
    }
    return base;
  }, []);

  /**
   * Edge colors reuse the community palette so the legend and graph agree.
   *
   * - intra-community: use the source node's community color at low alpha
   * - cross-community: neutral gray (reads as connective tissue)
   * - bridge:          slightly brighter gray to stand out as "long-range"
   * - dimmed:          when a community is highlighted, non-matching
   *                    edges fade out entirely
   */
  const linkColorFn = useCallback(
    (link: object): string => {
      const l = link as GraphLink;
      if (l.is_bridge) return BRIDGE_EDGE_COLOR;
      if (l.edge_type === "inter") return INTER_EDGE_COLOR;
      const src = l.source;
      const community =
        typeof src === "object" && src !== null
          ? (src as GraphNode).community
          : l._srcCommunity;
      if (!community) return INTER_EDGE_COLOR;
      if (highlightedCommunity !== null && community !== highlightedCommunity) {
        return "rgba(30,41,59,0.08)";
      }
      const hex = communityColorMap[community] ?? DEFAULT_NODE_COLOR;
      return hexToRgba(hex, 0.35);
    },
    [highlightedCommunity, communityColorMap],
  );

  // ---- Interaction callbacks --------------------------------------------- //
  const handleNodeClick = useCallback(
    (node: object) => {
      const n = node as GraphNode;
      const id = n.agent_id ?? n.id;
      // Open AgentInspector side drawer instead of full-page navigation so
      // the graph context is preserved. User can still navigate to the
      // standalone AgentDetail page from inside the inspector.
      selectAgent(id);
    },
    [selectAgent],
  );

  const handleNodeHover = useCallback((node: object | null) => {
    setHoverNode(node as GraphNode | null);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    if (highlightedCommunity) setHighlightedCommunity(null);
  }, [highlightedCommunity, setHighlightedCommunity]);

  // ---- Render tuning ------------------------------------------------------ //
  const nodeCount = graphData.nodes.length;
  const linkCount = graphData.links.length;
  const isLarge = nodeCount > 500;
  const isHuge = nodeCount > 2000;

  const rendererConfig = useMemo(
    () => ({
      antialias: !isLarge,
      alpha: true,
      powerPreference: "high-performance" as const,
    }),
    [isLarge],
  );

  // ---- GAP-7: Propagation particle callbacks ------------------------------ //
  //
  // Particle count tiers:
  //   - Active propagation link (in `activePropLinksRef`): 6 particles,
  //     colored by action, thick. These are the "something is happening
  //     between these two agents right now" moments the user actually
  //     wants to see.
  //   - Baseline intra-community link on small/medium graphs
  //     (`linkCount < LARGE_GRAPH_EDGE_THRESHOLD`): 1 dim white particle
  //     so the graph feels alive even when no fresh cascades are firing.
  //     Bumped from `< 200` → `< 2000` because real sims sit in the
  //     200-2000 edge range and the old threshold left them looking dead.
  //   - Huge graph (2000+ edges): no baseline — particles only on active
  //     propagation, otherwise the per-frame GPU cost from ~39k edges
  //     with 1 particle each kills frame rate.
  const LARGE_GRAPH_EDGE_THRESHOLD = 2000;

  const linkParticlesFn = useCallback(
    (link: object): number => {
      if (!propagationAnimEnabled) {
        return linkCount < LARGE_GRAPH_EDGE_THRESHOLD ? 1 : 0;
      }
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      if (activePropLinksRef.current.has(key)) return 6;
      return linkCount < LARGE_GRAPH_EDGE_THRESHOLD ? 1 : 0;
    },
    [propagationAnimEnabled, linkCount],
  );

  const linkParticleColorFn = useCallback(
    (link: object): string => {
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      // Active propagation links get their action color (share=green,
      // comment=blue, like=yellow, adopt=purple). Idle links get a dim
      // white so the baseline flow reads as connective tissue, not a
      // cascade signal.
      return activePropLinksRef.current.get(key) ?? "rgba(255,255,255,0.35)";
    },
    [],
  );

  const linkParticleWidthFn = useCallback(
    (link: object): number => {
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      // Active links get a chunky 3.5px width — visible on 1080p at
      // typical zoom without overwhelming the node rendering. Baseline
      // idle particles stay thin (0.6px) so they read as ambient.
      return activePropLinksRef.current.has(key) ? 3.5 : 0.6;
    },
    [],
  );

  return (
    <div
      data-testid="graph-panel"
      aria-label="3D social network graph visualization"
      className="relative w-full h-full overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse at center, #0f172a 0%, #020617 100%)",
      }}
    >
      <div
        ref={containerRef}
        data-testid="graph-cytoscape-container"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      >
        {dims.w > 0 && dims.h > 0 && (
          <ForceGraph3D
            ref={fgRef}
            width={dims.w}
            height={dims.h}
            graphData={graphData}
            backgroundColor="rgba(0,0,0,0)"
            showNavInfo={false}
            controlType="orbit"
            nodeLabel={(n: object) => (n as GraphNode).label}
            nodeColor={nodeColorFn}
            nodeVal={nodeValFn}
            nodeResolution={isHuge ? 4 : isLarge ? 6 : 10}
            nodeOpacity={0.9}
            linkColor={linkColorFn}
            linkWidth={0.3}
            linkOpacity={isLarge ? 0.35 : 0.55}
            linkDirectionalParticles={linkParticlesFn}
            linkDirectionalParticleColor={linkParticleColorFn}
            linkDirectionalParticleWidth={linkParticleWidthFn}
            // Slower particle travel (0.002 vs original 0.005) so the
            // eye can follow a cascade from source → target instead of
            // seeing a brief flash. On a 2s edge traversal at 60fps the
            // particle is clearly visible for its entire lifetime.
            linkDirectionalParticleSpeed={0.002}
            cooldownTicks={isHuge ? 40 : isLarge ? 80 : 150}
            warmupTicks={isHuge ? 5 : 10}
            d3AlphaDecay={0.04}
            d3VelocityDecay={0.35}
            enableNodeDrag={false}
            rendererConfig={rendererConfig}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            onBackgroundClick={handleBackgroundClick}
          />
        )}
      </div>

      {isLoading && (
        <div
          data-testid="graph-loading-overlay"
          className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm transition-opacity duration-300"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white" />
            <p className="text-xs text-white/70">Loading 3D network…</p>
          </div>
        </div>
      )}

      {/* Zoom tier badge — shows current LOD level (Close-up/Mid/Overview) */}
      <ZoomTierBadge tier={zoomTier} />

      {/* Comprehensive legend — communities + node states + edges.
          Communities are derived from the live graph so the list always
          reflects the actual simulation (not the hardcoded default profile).
          Stacked above the 3D Controls bottom-right overlay. */}
      <GraphLegend
        communities={graphCommunities}
        bottomOffsetPx={LEFT_LEGEND_OFFSET_PX}
      />

      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <h2 className="text-lg font-bold text-white">AI Social World — 3D</h2>
      </div>

      {/* Node / Edge count badge — top-right */}
      <div
        data-testid="graph-stats-badge"
        className="absolute top-4 right-4 z-10 pointer-events-none bg-slate-900/80 border border-slate-700/70 rounded-lg px-3 py-2 text-xs text-white shadow-lg backdrop-blur-sm"
      >
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end leading-tight">
            <span className="text-[10px] uppercase tracking-wide text-white/50">Nodes</span>
            <span className="font-semibold tabular-nums">{nodeCount.toLocaleString()}</span>
          </div>
          <div className="h-6 w-px bg-white/20" />
          <div className="flex flex-col items-end leading-tight">
            <span className="text-[10px] uppercase tracking-wide text-white/50">Edges</span>
            <span className="font-semibold tabular-nums">{linkCount.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Community color legend — left side, offset 200px above vertical
          center so it doesn't crowd the middle of the graph viewport.
          Counts come from the live graph; click a row to highlight that
          community (other communities dim). Click the active row again to
          clear the highlight. */}
      <div
        data-testid="graph-community-legend"
        className="absolute left-4 z-10 -translate-y-1/2 bg-slate-900/80 border border-slate-700/70 rounded-lg px-2 py-3 text-xs text-white shadow-lg backdrop-blur-sm"
        style={{ top: `calc(50% - ${LEFT_LEGEND_OFFSET_PX}px)` }}
      >
        <div className="text-[10px] uppercase tracking-wide text-white/50 mb-2 px-1 font-semibold flex items-center justify-between gap-3">
          <span>Communities</span>
          {highlightedCommunity !== null && (
            <button
              type="button"
              onClick={() => setHighlightedCommunity(null)}
              className="text-[9px] uppercase tracking-wide text-white/60 hover:text-white transition-colors"
              aria-label="Clear community highlight"
            >
              Clear
            </button>
          )}
        </div>
        <ul className="flex flex-col gap-0.5">
          {graphCommunities.length === 0 ? (
            <li className="px-2 py-1 text-[10px] text-white/40 italic">
              No communities loaded
            </li>
          ) : (
            graphCommunities.map((c) => {
              const isActive = highlightedCommunity === c.id;
              const dimmed = highlightedCommunity !== null && !isActive;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    data-testid={`legend-community-${c.id}`}
                    onClick={() =>
                      setHighlightedCommunity(isActive ? null : c.id)
                    }
                    aria-pressed={isActive}
                    aria-label={`Highlight ${c.name} community`}
                    className={`w-full flex items-center gap-2 px-2 py-1 rounded transition-all cursor-pointer ${
                      isActive
                        ? "bg-white/15 ring-1 ring-white/40"
                        : "hover:bg-white/10"
                    } ${dimmed ? "opacity-30" : "opacity-100"}`}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: c.color }}
                      aria-hidden="true"
                    />
                    <span className="flex-1 text-left text-white/90 truncate">
                      {c.name}
                    </span>
                    <span className="tabular-nums text-white/60 text-[11px] ml-2">
                      {c.count.toLocaleString()}
                    </span>
                  </button>
                </li>
              );
            })
          )}
        </ul>
      </div>

      {hoverNode && (
        <div
          data-testid="graph-hover-tooltip"
          // Lifted above the 3D Controls overlay (now bottom-right) so a
          // hovered node's metadata never sits underneath the controls hint.
          className="absolute bottom-20 right-4 z-10 pointer-events-none bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white shadow-lg"
        >
          <div className="font-semibold">{hoverNode.label}</div>
          <div className="text-white/70">
            Community:{" "}
            {hoverNode.community_name ??
              communityNameMap[hoverNode.community] ??
              hoverNode.community}
            {hoverNode.agent_type ? ` · ${hoverNode.agent_type}` : ""}
          </div>
          {typeof hoverNode.influence_score === "number" && (
            <div className="text-white/70">
              Influence: {hoverNode.influence_score.toFixed(2)}
            </div>
          )}
        </div>
      )}

      {/* 3D Controls hint — bottom-right corner. Moved off the bottom-left
          so it no longer overlaps the GraphLegend and the middle-left
          Communities legend when the viewport is narrow. */}
      <div className="absolute bottom-4 right-4 z-10 bg-black/40 rounded-lg p-3 backdrop-blur-sm text-xs text-white/70 pointer-events-none">
        <div className="font-semibold text-white/90 mb-1">3D Controls</div>
        <div>Left-drag: rotate · Scroll: zoom · Right-drag: pan</div>
      </div>
    </div>
  );
}
