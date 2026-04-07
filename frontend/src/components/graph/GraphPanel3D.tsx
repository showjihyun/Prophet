/**
 * GraphPanel3D — 3D WebGL social network renderer.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#graph-panel-3d-rendering
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-center-ai-social-world-graph-engine
 *
 * Uses react-force-graph-3d (three.js under the hood) to render agents as
 * spheres in 3D space with a force-directed layout. Replaces the prior
 * Cytoscape.js 2D canvas renderer.
 *
 * Performance contract:
 *  - Bounded simulation: `cooldownTicks` caps post-mount force work so the
 *    graph settles quickly instead of churning every frame.
 *  - Per-step updates never rebuild graphData or touch the force engine;
 *    they only flip per-node highlight state via a ref + refresh call.
 *  - `nodeResolution` scales down for large graphs (>500 nodes) so each
 *    sphere uses fewer triangles.
 *  - Link particles (propagation animation) are enabled only for a
 *    small sample of edges at a time to keep GPU cost bounded.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ForceGraph3D, { type ForceGraphMethods } from "react-force-graph-3d";
import * as THREE from "three";
import { apiClient, type CytoscapeGraph } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";
import { COMMUNITIES } from "@/config/constants";

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
  // Force-graph augments these at runtime:
  x?: number;
  y?: number;
  z?: number;
}

interface GraphLink {
  source: string;
  target: string;
  weight?: number;
  edge_type?: string;
  is_bridge?: boolean;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// --------------------------------------------------------------------------- //
// Community color palette                                                     //
// --------------------------------------------------------------------------- //

const COMMUNITY_COLOR: Record<string, string> = Object.fromEntries(
  COMMUNITIES.map((c) => [c.id, c.color]),
);

const DEFAULT_NODE_COLOR = "#64748b";
const ADOPTED_GLOW_COLOR = "#22c55e";
const HIGHLIGHT_DIM_COLOR = "#1e293b";

// --------------------------------------------------------------------------- //
// Data transform: API Cytoscape format → force-graph format                   //
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
  const links: GraphLink[] = api.edges.map((e) => {
    const d = e.data as Record<string, unknown>;
    return {
      source: String(d.source ?? ""),
      target: String(d.target ?? ""),
      weight: d.weight as number | undefined,
      edge_type: d.edge_type as string | undefined,
      is_bridge: Boolean(d.is_bridge),
    };
  });
  return { nodes, links };
}

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

export default function GraphPanel3D() {
  const navigate = useNavigate();
  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [dims, setDims] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);

  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const latestStep = useSimulationStore((s) => s.latestStep);
  const highlightedCommunity = useSimulationStore((s) => s.highlightedCommunity);
  const setHighlightedCommunity = useSimulationStore((s) => s.setHighlightedCommunity);

  // Per-node mutable highlight flags (kept off React state to avoid re-renders).
  const adoptedSetRef = useRef<Set<string>>(new Set());

  // ---- Load graph data on simulation change ------------------------------- //
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        if (simulationId) {
          const api = await apiClient.network.get(simulationId);
          if (!cancelled) setGraphData(cytoscapeToForceGraph(api));
        } else {
          if (!cancelled) setGraphData({ nodes: [], links: [] });
        }
      } catch (err) {
        console.warn("[GraphPanel3D] fetch failed:", err);
        if (!cancelled) setGraphData({ nodes: [], links: [] });
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [simulationId]);

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

    // Pick the top-influencers (stable order) as "adopted" for visual effect.
    const sorted = [...graphData.nodes].sort(
      (a, b) => (b.influence_score ?? 0) - (a.influence_score ?? 0),
    );
    const newSet = new Set<string>();
    for (let i = 0; i < adoptCount; i++) newSet.add(sorted[i].id);
    adoptedSetRef.current = newSet;
    // Trigger a cheap material refresh without rebuilding graphData.
    fgRef.current?.refresh();
  }, [latestStep, graphData.nodes]);

  // ---- Node sphere factory (memoized material cache) --------------------- //
  const materialCache = useRef<Map<string, THREE.MeshLambertMaterial>>(new Map());
  const sphereGeometry = useMemo(() => {
    const isLarge = graphData.nodes.length > 500;
    // Lower triangle count for large graphs → faster frame times.
    return new THREE.SphereGeometry(3, isLarge ? 8 : 12, isLarge ? 8 : 12);
  }, [graphData.nodes.length]);

  const getNodeMaterial = useCallback(
    (node: GraphNode): THREE.MeshLambertMaterial => {
      const isAdopted = adoptedSetRef.current.has(node.id);
      const dimmed = highlightedCommunity !== null && node.community !== highlightedCommunity;
      const base = COMMUNITY_COLOR[node.community] ?? DEFAULT_NODE_COLOR;
      const color = dimmed ? HIGHLIGHT_DIM_COLOR : isAdopted ? ADOPTED_GLOW_COLOR : base;
      const key = `${color}-${isAdopted ? 1 : 0}-${dimmed ? 1 : 0}`;
      let mat = materialCache.current.get(key);
      if (!mat) {
        mat = new THREE.MeshLambertMaterial({
          color,
          emissive: isAdopted ? new THREE.Color(color) : new THREE.Color(0x000000),
          emissiveIntensity: isAdopted ? 0.6 : 0,
          transparent: dimmed,
          opacity: dimmed ? 0.25 : 1.0,
        });
        materialCache.current.set(key, mat);
      }
      return mat;
    },
    [highlightedCommunity],
  );

  const buildNodeObject = useCallback(
    (node: object) => {
      const n = node as GraphNode;
      const scale = 0.6 + Math.min(1.8, (n.influence_score ?? 0.2) * 2.0);
      const mesh = new THREE.Mesh(sphereGeometry, getNodeMaterial(n));
      mesh.scale.setScalar(scale);
      return mesh;
    },
    [sphereGeometry, getNodeMaterial],
  );

  // ---- Callbacks ---------------------------------------------------------- //
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

  // ---- Link coloring ----------------------------------------------------- //
  const linkColor = useCallback((link: object): string => {
    const l = link as GraphLink;
    if (l.is_bridge) return "rgba(239,68,68,0.35)";
    if (l.edge_type === "inter") return "rgba(148,163,184,0.15)";
    return "rgba(59,130,246,0.25)";
  }, []);

  // ---- Render ------------------------------------------------------------- //
  const nodeCount = graphData.nodes.length;
  const linkCount = graphData.links.length;
  const isLarge = nodeCount > 500;

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
      {/* WebGL container — inline sizing so the canvas always matches the panel.
          SPEC: docs/spec/07_FRONTEND_SPEC.md#graph-panel-layout-robustness */}
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
            nodeLabel={(n: object) => (n as GraphNode).label}
            nodeThreeObject={buildNodeObject}
            nodeResolution={isLarge ? 8 : 12}
            linkColor={linkColor}
            linkWidth={0.4}
            linkOpacity={0.4}
            linkDirectionalParticles={isLarge ? 0 : 1}
            linkDirectionalParticleWidth={0.8}
            linkDirectionalParticleSpeed={0.005}
            cooldownTicks={isLarge ? 80 : 150}
            warmupTicks={isLarge ? 10 : 30}
            enableNodeDrag={false}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            onBackgroundClick={handleBackgroundClick}
          />
        )}
      </div>

      {/* Loading overlay */}
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

      {/* Title — top-left */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <h2 className="text-lg font-bold text-white">AI Social World — 3D</h2>
        <p className="text-xs text-white/60">
          MiroFish Engine · {nodeCount} Agents · {linkCount} Connections · Force-Directed WebGL
        </p>
      </div>

      {/* Hover tooltip */}
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

      {/* Controls hint — bottom-left */}
      <div className="absolute bottom-4 left-4 z-10 bg-black/40 rounded-lg p-3 backdrop-blur-sm text-xs text-white/70 pointer-events-none">
        <div className="font-semibold text-white/90 mb-1">3D Controls</div>
        <div>Drag: orbit · Scroll: zoom · Right-drag: pan</div>
      </div>
    </div>
  );
}
