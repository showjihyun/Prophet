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
import { useNavigate } from "react-router-dom";
import ForceGraph3D, { type ForceGraphMethods } from "react-force-graph-3d";
import { type CytoscapeGraph } from "../../api/client";
import { useNetwork } from "../../api/queries";
import { useSimulationStore } from "../../store/simulationStore";
import { COMMUNITIES } from "@/config/constants";
import type { PropagationPair } from "@/types/simulation";
import { getAnimationTier, TIER_LIMITS, ACTION_COLORS } from "./propagationAnimationUtils";

// --------------------------------------------------------------------------- //
// Types                                                                       //
// --------------------------------------------------------------------------- //

interface GraphNode {
  id: string;
  label: string;
  community: string;
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
// Community color palette — single source of truth for legend + graph         //
// --------------------------------------------------------------------------- //

const COMMUNITY_COLOR: Record<string, string> = Object.fromEntries(
  COMMUNITIES.map((c) => [c.id, c.color]),
);

const DEFAULT_NODE_COLOR = "#64748b";
const ADOPTED_GLOW_COLOR = "#22c55e";
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

// --------------------------------------------------------------------------- //
// Data transform: API Cytoscape format -> force-graph format                  //
// --------------------------------------------------------------------------- //

function cytoscapeToForceGraph(api: CytoscapeGraph): GraphData {
  const nodes: GraphNode[] = api.nodes.map((n) => {
    const d = n.data as Record<string, unknown>;
    return {
      id: String(d.id ?? ""),
      label: String(d.label ?? ""),
      community: String(d.community ?? "A"),
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
  const navigate = useNavigate();
  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);

  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const latestStep = useSimulationStore((s) => s.latestStep);
  const highlightedCommunity = useSimulationStore((s) => s.highlightedCommunity);
  const setHighlightedCommunity = useSimulationStore((s) => s.setHighlightedCommunity);
  const propagationAnimEnabled = useSimulationStore((s) => s.propagationAnimationsEnabled);

  // Per-node mutable highlight flags kept off React state to avoid re-renders.
  const adoptedSetRef = useRef<Set<string>>(new Set());

  // GAP-7: Active propagation link set (source→target keys that should show particles)
  const activePropLinksRef = useRef<Map<string, string>>(new Map());
  const propTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    if ("ResizeObserver" in window) {
      const ro = new ResizeObserver(update);
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
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

  // ---- GAP-7: Propagation animation effect -------------------------------- //
  useEffect(() => {
    if (!propagationAnimEnabled || !latestStep?.propagation_pairs?.length) {
      activePropLinksRef.current.clear();
      return;
    }

    // Determine current zoom tier and limit
    const fg = fgRef.current;
    const camera = fg ? (fg as unknown as { camera: () => { position: { length: () => number } } }).camera?.() : null;
    const zoomDist = camera?.position?.length?.() ?? 500;
    // Normalize zoom: closer = higher value (inverse distance, capped at 1.0)
    const normalizedZoom = Math.min(1.0, 300 / Math.max(zoomDist, 1));
    const tier = getAnimationTier(normalizedZoom);
    const limit = TIER_LIMITS[tier];

    // Filter out "ignore" actions and take top pairs by probability
    const pairs = (latestStep.propagation_pairs as PropagationPair[])
      .filter((p) => p.action in ACTION_COLORS)
      .slice(0, limit);

    const newMap = new Map<string, string>();
    for (const p of pairs) {
      const key = `${p.source}__${p.target}`;
      newMap.set(key, ACTION_COLORS[p.action] ?? "#94a3b8");
    }
    activePropLinksRef.current = newMap;
    fgRef.current?.refresh();

    // Clear particles after CASCADE_TTL_MS (fade out)
    if (propTimerRef.current) clearTimeout(propTimerRef.current);
    propTimerRef.current = setTimeout(() => {
      activePropLinksRef.current.clear();
      fgRef.current?.refresh();
    }, 8_000);

    return () => {
      if (propTimerRef.current) clearTimeout(propTimerRef.current);
    };
  }, [propagationAnimEnabled, latestStep]);

  // ---- Color + size callbacks (built-in InstancedMesh path) --------------- //
  const nodeColorFn = useCallback(
    (node: object): string => {
      const n = node as GraphNode;
      const dimmed =
        highlightedCommunity !== null && n.community !== highlightedCommunity;
      if (dimmed) return HIGHLIGHT_DIM_COLOR;
      if (adoptedSetRef.current.has(n.id)) return ADOPTED_GLOW_COLOR;
      return COMMUNITY_COLOR[n.community] ?? DEFAULT_NODE_COLOR;
    },
    [highlightedCommunity],
  );

  const nodeValFn = useCallback((node: object): number => {
    const n = node as GraphNode;
    return 1 + Math.min(6, (n.influence_score ?? 0.2) * 8.0);
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
      const hex = COMMUNITY_COLOR[community] ?? DEFAULT_NODE_COLOR;
      return hexToRgba(hex, 0.35);
    },
    [highlightedCommunity],
  );

  // ---- Interaction callbacks --------------------------------------------- //
  const handleNodeClick = useCallback(
    (node: object) => {
      const n = node as GraphNode;
      const id = n.agent_id ?? n.id;
      navigate(`/agents/${id}`);
    },
    [navigate],
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

  // Per-community node counts for the left legend overlay. Recomputed only
  // when the underlying node list changes (cheap O(n) single pass).
  const communityCounts = useMemo<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    for (const n of graphData.nodes) {
      counts[n.community] = (counts[n.community] ?? 0) + 1;
    }
    return counts;
  }, [graphData.nodes]);

  const rendererConfig = useMemo(
    () => ({
      antialias: !isLarge,
      alpha: true,
      powerPreference: "high-performance" as const,
    }),
    [isLarge],
  );

  // ---- GAP-7: Propagation particle callbacks ------------------------------ //
  const linkParticlesFn = useCallback(
    (link: object): number => {
      if (!propagationAnimEnabled) return linkCount < 200 ? 1 : 0;
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      if (activePropLinksRef.current.has(key)) return 4;
      return linkCount < 200 ? 1 : 0;
    },
    [propagationAnimEnabled, linkCount],
  );

  const linkParticleColorFn = useCallback(
    (link: object): string => {
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      return activePropLinksRef.current.get(key) ?? "rgba(255,255,255,0.6)";
    },
    [],
  );

  const linkParticleWidthFn = useCallback(
    (link: object): number => {
      const l = link as GraphLink;
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      const key = `${srcId}__${tgtId}`;
      return activePropLinksRef.current.has(key) ? 2.0 : 0.8;
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
            linkDirectionalParticleSpeed={0.005}
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

      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <h2 className="text-lg font-bold text-white">AI Social World — 3D</h2>
        <p className="text-xs text-white/60">
          MiroFish Engine · three.js WebGL
        </p>
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

      {/* Community color legend — left side, vertically centered.
          Single source of truth: COMMUNITIES from @/config/constants.
          Counts come from the live graph; rows with 0 nodes are still
          shown so the user can see the full palette.
          Click a row to highlight that community (other communities dim
          in both the graph and this legend). Click the active row again
          to clear the highlight. */}
      <div
        data-testid="graph-community-legend"
        className="absolute top-1/2 left-4 z-10 -translate-y-1/2 bg-slate-900/80 border border-slate-700/70 rounded-lg px-2 py-3 text-xs text-white shadow-lg backdrop-blur-sm"
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
          {COMMUNITIES.map((c) => {
            const count = communityCounts[c.id] ?? 0;
            const isActive = highlightedCommunity === c.id;
            const dimmed =
              highlightedCommunity !== null && !isActive;
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
                  <span className="flex-1 text-left text-white/90">{c.name}</span>
                  <span className="tabular-nums text-white/60 text-[11px] ml-2">
                    {count.toLocaleString()}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {hoverNode && (
        <div
          data-testid="graph-hover-tooltip"
          className="absolute bottom-4 right-4 z-10 pointer-events-none bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white shadow-lg"
        >
          <div className="font-semibold">{hoverNode.label}</div>
          <div className="text-white/70">
            Community: {hoverNode.community}
            {hoverNode.agent_type ? ` · ${hoverNode.agent_type}` : ""}
          </div>
          {typeof hoverNode.influence_score === "number" && (
            <div className="text-white/70">
              Influence: {hoverNode.influence_score.toFixed(2)}
            </div>
          )}
        </div>
      )}

      <div className="absolute bottom-4 left-4 z-10 bg-black/40 rounded-lg p-3 backdrop-blur-sm text-xs text-white/70 pointer-events-none">
        <div className="font-semibold text-white/90 mb-1">3D Controls</div>
        <div>Left-drag: rotate · Scroll: zoom · Right-drag: pan</div>
      </div>
    </div>
  );
}
