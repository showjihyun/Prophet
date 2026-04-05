/**
 * GraphPanel — AI Social World Graph Engine (Zone 2 Center).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-center-ai-social-world-graph-engine
 * @spec docs/spec/ui/DESIGN.md#5-graph-engine-visual-spec
 *
 * Cytoscape.js canvas renderer with force-directed layout,
 * community-colored nodes, and interactive selection.
 *
 * Performance optimizations (GAP-5, 10K agent target):
 *  - textureOnViewport, hideEdgesOnViewport, motionBlur, pixelRatio:1
 *  - LOD zoom-based label/edge visibility
 *  - cy.batch() for step-result updates
 *  - Edge opacity reduction + non-bridge hiding at node count > 2000
 *  - Real FPS counter via requestAnimationFrame
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { apiClient, type CytoscapeGraph } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";
import { COMMUNITIES } from "@/config/constants";

// ---------------------------------------------------------------------------
// Cascade shader animation CSS (injected once at module load).
// GAP-6: pulse/ripple/glow effects for viral cascade events.
// Cytoscape canvas does not support CSS on canvas nodes, so node/edge
// animation uses Cytoscape's animate() API; CSS keyframes only affect DOM
// overlay elements (the cascade badge glow ring).
// ---------------------------------------------------------------------------
const CASCADE_STYLE_ID = "mcasp-cascade-style";
if (typeof document !== "undefined" && !document.getElementById(CASCADE_STYLE_ID)) {
  const _cascadeStyleEl = document.createElement("style");
  _cascadeStyleEl.id = CASCADE_STYLE_ID;
  _cascadeStyleEl.textContent = `
    @keyframes cascade-badge-glow {
      0%,100% { box-shadow: 0 0 0 0 rgba(250,204,21,0); }
      50%      { box-shadow: 0 0 20px 8px rgba(250,204,21,0.55); }
    }
    .cascade-badge-active { animation: cascade-badge-glow 1.6s ease-in-out infinite; }
  `;
  document.head.appendChild(_cascadeStyleEl);
}

/** How long (ms) cascade highlights stay active after a new cascade event. */
const CASCADE_TTL_MS = 8000;

const COMMUNITY_COLOR: Record<string, string> = Object.fromEntries(
  COMMUNITIES.map((c) => [c.id, c.color]),
);

const LEGEND_ITEMS = COMMUNITIES.map((c) => ({
  name: c.name,
  color: c.color,
  count: c.size.toString(),
}));

// ---------------------------------------------------------------------------
// Mock data generator (~200 nodes, ~400 edges)
// ---------------------------------------------------------------------------
interface MockNode {
  data: {
    id: string;
    label: string;
    community: string;
    agent_type: string;
    influence_score: number;
    adopted: boolean;
  };
}

interface MockEdge {
  data: {
    id: string;
    source: string;
    target: string;
    weight: number;
    is_bridge: boolean;
    edge_type: string;
  };
}

function generateMockGraphData(): { nodes: MockNode[]; edges: MockEdge[] } {
  const nodes: MockNode[] = [];
  const edges: MockEdge[] = [];
  const rng = mulberry32(42); // deterministic seed for stable layout

  // --- Nodes ---
  let nodeIndex = 0;
  const communityNodeIds: Record<string, string[]> = {};

  for (const community of COMMUNITIES) {
    communityNodeIds[community.id] = [];
    for (let i = 0; i < community.size; i++) {
      const id = `n${nodeIndex++}`;
      const isInfluencer = rng() < 0.1;
      const isBridge = community.id === "E";
      nodes.push({
        data: {
          id,
          label: `Agent ${id}`,
          community: community.id,
          agent_type: isBridge ? "bridge" : isInfluencer ? "influencer" : "normal",
          influence_score: isBridge ? 0.8 : isInfluencer ? rng() * 0.4 + 0.6 : rng() * 0.3,
          adopted: rng() < 0.15,
        },
      });
      communityNodeIds[community.id].push(id);
    }
  }

  // --- Intra-community edges ---
  let edgeIndex = 0;
  for (const community of COMMUNITIES) {
    const ids = communityNodeIds[community.id];
    const targetEdges = Math.floor(ids.length * 2.5);
    for (let i = 0; i < targetEdges; i++) {
      const src = ids[Math.floor(rng() * ids.length)];
      const tgt = ids[Math.floor(rng() * ids.length)];
      if (src !== tgt) {
        edges.push({
          data: {
            id: `e${edgeIndex++}`,
            source: src,
            target: tgt,
            weight: rng(),
            is_bridge: false,
            edge_type: "intra",
          },
        });
      }
    }
  }

  // --- Inter-community edges (sparse) ---
  const allCommunityKeys = Object.keys(communityNodeIds);
  for (let i = 0; i < 30; i++) {
    const c1 = allCommunityKeys[Math.floor(rng() * allCommunityKeys.length)];
    let c2 = allCommunityKeys[Math.floor(rng() * allCommunityKeys.length)];
    if (c1 === c2) c2 = allCommunityKeys[(allCommunityKeys.indexOf(c1) + 1) % allCommunityKeys.length];
    const ids1 = communityNodeIds[c1];
    const ids2 = communityNodeIds[c2];
    const src = ids1[Math.floor(rng() * ids1.length)];
    const tgt = ids2[Math.floor(rng() * ids2.length)];
    edges.push({
      data: {
        id: `e${edgeIndex++}`,
        source: src,
        target: tgt,
        weight: rng() * 0.5,
        is_bridge: c1 === "E" || c2 === "E",
        edge_type: c1 === "E" || c2 === "E" ? "bridge" : "inter",
      },
    });
  }

  return { nodes, edges };
}

/** Deterministic PRNG (Mulberry32) for reproducible mock data. */
function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------------------
// Cytoscape style sheet (per DESIGN.md §5)
// ---------------------------------------------------------------------------
function nodeColor(ele: cytoscape.NodeSingular): string {
  const community = ele.data("community") as string;
  return COMMUNITY_COLOR[community] ?? "#888888";
}

const CY_STYLE: cytoscape.Stylesheet[] = [
  // -- Default node --
  {
    selector: "node",
    style: {
      width: 5,
      height: 5,
      "background-color": nodeColor as unknown as string,
      label: "",
      "border-width": 0,
      "overlay-opacity": 0,
    },
  },
  // -- Influencer (glow via underlay) --
  {
    selector: 'node[agent_type = "influencer"]',
    style: {
      width: 10,
      height: 10,
      "underlay-color": nodeColor as unknown as string,
      "underlay-padding": 4,
      "underlay-opacity": 0.3,
      "underlay-shape": "ellipse",
    },
  },
  // -- Bridge node (red glow via underlay) --
  {
    selector: 'node[agent_type = "bridge"]',
    style: {
      width: 7,
      height: 7,
      "background-color": "#ef4444",
      "underlay-color": "#ef4444",
      "underlay-padding": 4,
      "underlay-opacity": 0.25,
      "underlay-shape": "ellipse",
    },
  },
  // -- Selected node (green ring via border + underlay) --
  {
    selector: "node:selected",
    style: {
      width: 20,
      height: 20,
      "border-width": 3,
      "border-color": "#ffffff",
      "underlay-color": "#22c55e",
      "underlay-padding": 8,
      "underlay-opacity": 0.4,
      "underlay-shape": "ellipse",
      label: "data(label)",
      "font-size": 8,
      color: "#ffffff",
      "text-valign": "top",
      "text-margin-y": -6,
    },
  },
  // -- Adopted node (faint pulse indicator) --
  {
    selector: "node[adopted]",
    style: {
      "border-width": 1,
      "border-color": "#22c55e",
    },
  },
  // -- Live adopted node (updated per simulation step) --
  {
    selector: ".adopted-live",
    style: {
      "border-width": 2,
      "border-color": "#22c55e",
      width: 8,
      height: 8,
    },
  },
  // -- Cascade: nodes involved in viral cascade (pulsing golden border) --
  {
    selector: ".cascade-node",
    style: {
      "border-width": 2,
      "border-color": "#facc15",
      "underlay-color": "#facc15",
      "underlay-padding": 3,
      "underlay-opacity": 0.2,
      "underlay-shape": "ellipse",
    },
  },
  // -- Cascade: origin node (larger + bright golden glow) --
  {
    selector: ".cascade-origin",
    style: {
      width: 14,
      height: 14,
      "border-width": 3,
      "border-color": "#facc15",
      "underlay-color": "#facc15",
      "underlay-padding": 6,
      "underlay-opacity": 0.45,
      "underlay-shape": "ellipse",
    },
  },
  // -- Cascade: edges with active propagation --
  {
    selector: ".cascade-edge",
    style: {
      width: 1.5,
      "line-color": "#facc15",
      opacity: 0.6,
    },
  },
  // -- Default edge (intra-community) --
  {
    selector: "edge",
    style: {
      width: 0.5,
      "line-color": "#3b82f6",
      opacity: 0.15,
      "curve-style": "haystack",
    },
  },
  // -- Inter-community edge --
  {
    selector: 'edge[edge_type = "inter"]',
    style: {
      width: 1,
      "line-color": "#ffffff",
      opacity: 0.06,
    },
  },
  // -- Bridge edge --
  {
    selector: 'edge[edge_type = "bridge"]',
    style: {
      width: 1,
      "line-color": "#ef4444",
      opacity: 0.12,
    },
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function GraphPanel() {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  useEffect(() => { navigateRef.current = navigate; });
  const cyRef = useRef<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [hoverInfo, setHoverInfo] = useState<{
    label: string;
    community: string;
    type: string;
    influenceScore: number;
    connections: number;
    x: number;
    y: number;
  } | null>(null);
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);
  const [legendItems, setLegendItems] = useState(LEGEND_ITEMS);
  const [fps, setFps] = useState(60);
  const fpsFramesRef = useRef<number[]>([]);
  const fpsRafRef = useRef<number | null>(null);
  // Track how many cascade events we've already animated to detect new ones
  const lastCascadeCountRef = useRef(0);
  const cascadeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);
  const steps = useSimulationStore((s) => s.steps);
  const highlightedCommunity = useSimulationStore((s) => s.highlightedCommunity);
  const setHighlightedCommunity = useSimulationStore((s) => s.setHighlightedCommunity);

  // --- Initialize Cytoscape ---
  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    async function loadGraph() {
      let graphData: CytoscapeGraph;
      try {
        if (simulationId) {
          graphData = await apiClient.network.get(simulationId);
        } else {
          graphData = generateMockGraphData();
        }
      } catch {
        graphData = generateMockGraphData();
      }
      if (cancelled || !containerRef.current) return;

      // Compute legend from real data
      const commCounts: Record<string, number> = {};
      for (const n of graphData.nodes) {
        const cid = (n.data.community as string) ?? "?";
        commCounts[cid] = (commCounts[cid] ?? 0) + 1;
      }
      setLegendItems(
        COMMUNITIES.map((c) => ({
          name: c.name,
          color: c.color,
          count: String(commCounts[c.id] ?? 0),
        })),
      );

      initCytoscape(graphData);
    }

    function initCytoscape(graphData: CytoscapeGraph) {
      if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.nodes,
        edges: graphData.edges,
      },
      style: CY_STYLE,
      layout: {
        name: "cose",
        idealEdgeLength: 50,
        nodeOverlap: 8,
        refresh: 20,
        fit: true,
        padding: 40,
        randomize: false,
        componentSpacing: 60,
        nodeRepulsion: 6000,
        edgeElasticity: 80,
        nestingFactor: 1.2,
        gravity: 0.3,
        numIter: 800,
        animate: false,
      } as cytoscape.CoseLayoutOptions,

      // Performance options (GAP-5: 10K agent target)
      textureOnViewport: true,
      hideEdgesOnViewport: true,
      motionBlur: true,
      pixelRatio: 1,

      // Viewport culling limits
      minZoom: 0.05,
      maxZoom: 3.0,
      // wheelSensitivity removed — Cytoscape default (1.0) used
    });

    const totalNodes = cy.nodes().length;
    const totalEdges = cy.edges().length;
    setNodeCount(totalNodes);
    setEdgeCount(totalEdges);

    // --- Edge bundling for large graphs (>2000 nodes) ---
    if (totalNodes > 2000) {
      cy.batch(() => {
        cy.edges().style("opacity", 0.05);
        cy.edges('[edge_type != "bridge"]').style("display", "none");
      });
    }

    // --- LOD: zoom-dependent label & edge visibility ---
    function applyLOD() {
      const z = cy.zoom();
      cy.batch(() => {
        if (z < 0.3) {
          // Far out: no labels, straight-line edges
          cy.nodes().style("label", "");
          cy.edges().style("curve-style", "haystack");
        } else if (z < 0.7) {
          // Mid: labels only for high-influence nodes
          cy.nodes().forEach((node) => {
            const score = node.data("influence_score") as number;
            node.style("label", score > 0.8 ? "data(label)" : "");
          });
          cy.edges().style("curve-style", "haystack");
        } else {
          // Close: all labels, full detail
          cy.nodes().style("label", "data(label)");
          cy.edges().style("curve-style", "bezier");
        }
      });
    }
    cy.on("zoom", applyLOD);
    // Apply initial LOD state
    applyLOD();

    // --- Edge coloring by source community ---
    cy.edges().forEach((edge) => {
      const edgeType = edge.data("edge_type") as string;
      if (edgeType === "intra") {
        const srcNode = edge.source();
        const community = srcNode.data("community") as string;
        const color = COMMUNITY_COLOR[community] ?? "#3b82f6";
        edge.style("line-color", color);
      }
    });

    // --- Click: select node ---
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      setSelectedAgent(node.data("id") as string);
      navigateRef.current(`/agents/${node.data("id")}`);
    });

    // --- Click background: deselect ---
    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        setSelectedAgent(null);
      }
    });

    // --- Hover: tooltip ---
    cy.on("mouseover", "node", (evt: EventObject) => {
      const node = evt.target;
      const pos = node.renderedPosition();
      setHoverInfo({
        label: node.data("label") as string,
        community:
          COMMUNITIES.find((c) => c.id === node.data("community"))?.name ??
          "Unknown",
        type: node.data("agent_type") as string,
        influenceScore: node.data("influence_score") as number,
        connections: node.connectedEdges().length,
        x: pos.x,
        y: pos.y,
      });
      containerRef.current!.style.cursor = "pointer";
    });

    cy.on("mouseout", "node", () => {
      setHoverInfo(null);
      containerRef.current!.style.cursor = "default";
    });

    cyRef.current = cy;
    }

    loadGraph();

    return () => {
      cancelled = true;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [simulationId]);

  // --- FPS counter via requestAnimationFrame ---
  useEffect(() => {
    let running = true;

    function tick(now: number) {
      if (!running) return;
      const frames = fpsFramesRef.current;
      frames.push(now);
      // Keep only the last 60 timestamps (one second window at 60fps)
      while (frames.length > 0 && now - frames[0] > 1000) {
        frames.shift();
      }
      setFps(frames.length);
      fpsRafRef.current = requestAnimationFrame(tick);
    }

    fpsRafRef.current = requestAnimationFrame(tick);
    return () => {
      running = false;
      if (fpsRafRef.current !== null) {
        cancelAnimationFrame(fpsRafRef.current);
        fpsRafRef.current = null;
      }
    };
  }, []);

  // --- Update node adoption state on each new simulation step ---
  // Uses cy.batch() to coalesce all DOM/style mutations into one repaint (GAP-5)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || steps.length === 0) return;
    const latestStep = steps[steps.length - 1];
    const adoptionRate = latestStep.adoption_rate || 0;

    const nodes = cy.nodes();
    const total = nodes.length;
    const adoptCount = Math.floor(total * adoptionRate);

    // Pre-sort outside batch to keep batch closure lightweight
    const sorted = nodes.toArray().sort(
      (a, b) => ((b.data("influence_score") as number) || 0) - ((a.data("influence_score") as number) || 0),
    );
    const adoptedSet = new Set(sorted.slice(0, adoptCount).map((n) => n.id()));

    // Single batched mutation — one repaint instead of N individual updates
    cy.batch(() => {
      nodes.forEach((node) => {
        if (adoptedSet.has(node.id())) {
          node.addClass("adopted-live");
        } else {
          node.removeClass("adopted-live");
        }
      });
    });
  }, [steps]);

  // --- Community highlight: dim non-matching nodes when a community is selected ---
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (!highlightedCommunity) {
      cy.nodes().style("opacity", 1);
      cy.edges().removeStyle("opacity");
      return;
    }
    cy.nodes().forEach((node) => {
      const comm = node.data("community") as string;
      node.style("opacity", comm === highlightedCommunity ? 1 : 0.15);
    });
    cy.edges().style("opacity", 0.05);
  }, [highlightedCommunity]);

  // --- GAP-6: Cascade shader animations via Cytoscape animate() API ---
  // Triggered when a new cascade event appears in emergentEvents.
  // - Cascade origin node: larger size + golden glow (cascade-origin class)
  // - Nodes in cascade: pulsing golden border (cascade-node class)
  // - Cascade edges: animate opacity 0.3 → 1.0 → 0.3 (cascade-edge class)
  // All effects auto-clear after CASCADE_TTL_MS.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || emergentEvents.length === 0) return;

    // Only fire when the event count has grown (new event arrived)
    if (emergentEvents.length <= lastCascadeCountRef.current) return;
    lastCascadeCountRef.current = emergentEvents.length;

    const latestEvent = emergentEvents[emergentEvents.length - 1];
    const isCascadeEvent =
      latestEvent.event_type.toLowerCase().includes("cascade") ||
      latestEvent.event_type.toLowerCase().includes("viral");

    if (!isCascadeEvent) return;

    // Clear any previous cascade highlight timeout
    if (cascadeTimeoutRef.current !== null) {
      clearTimeout(cascadeTimeoutRef.current);
      cascadeTimeoutRef.current = null;
    }

    // Remove stale cascade classes before applying new ones
    cy.batch(() => {
      cy.elements().removeClass("cascade-node cascade-origin cascade-edge");
    });

    // Pick origin node: highest-influence node in the graph
    const nodes = cy.nodes();
    const originNode = nodes.max((node) => (node.data("influence_score") as number) || 0).ele;

    // Pick cascade participant nodes: top ~15% by influence score
    const sortedNodes = nodes.toArray().sort(
      (a, b) => ((b.data("influence_score") as number) || 0) - ((a.data("influence_score") as number) || 0),
    );
    const cascadeCount = Math.max(1, Math.floor(sortedNodes.length * 0.15));
    const cascadeNodes = sortedNodes.slice(0, cascadeCount);

    // Apply classes (triggers CY_STYLE rules defined above)
    cy.batch(() => {
      cascadeNodes.forEach((node) => node.addClass("cascade-node"));
      originNode.addClass("cascade-origin");

      // Mark edges connected to cascade nodes
      cascadeNodes.forEach((node) => {
        node.connectedEdges().addClass("cascade-edge");
      });
    });

    // Animate origin node: scale border-width 2 → 5 → 2 repeating (pulse effect)
    // Cytoscape animate() does not support looping natively; we chain two animations.
    function pulseBorder(node: cytoscape.NodeSingular, iteration: number) {
      if (iteration > 4 || !cyRef.current) return; // stop after ~8s
      node.animate(
        { style: { "border-width": 5 } },
        {
          duration: 700,
          easing: "ease-in-out",
          complete: () => {
            node.animate(
              { style: { "border-width": 2 } },
              {
                duration: 700,
                easing: "ease-in-out",
                complete: () => pulseBorder(node, iteration + 1),
              },
            );
          },
        },
      );
    }
    pulseBorder(originNode as cytoscape.NodeSingular, 0);

    // Animate cascade edges: opacity 0.15 → 0.8 → 0.15 (2s cycle × 4)
    function pulseEdgeOpacity(edges: cytoscape.EdgeCollection, iteration: number) {
      if (iteration > 3 || !cyRef.current) return;
      edges.animate(
        { style: { opacity: 0.8 } },
        {
          duration: 1000,
          easing: "ease-in-out",
          complete: () => {
            edges.animate(
              { style: { opacity: 0.15 } },
              {
                duration: 1000,
                easing: "ease-in-out",
                complete: () => pulseEdgeOpacity(edges, iteration + 1),
              },
            );
          },
        },
      );
    }
    const cascadeEdges = cy.edges(".cascade-edge");
    if (cascadeEdges.length > 0) {
      pulseEdgeOpacity(cascadeEdges, 0);
    }

    // Auto-clear after TTL
    cascadeTimeoutRef.current = setTimeout(() => {
      if (!cyRef.current) return;
      cy.batch(() => {
        cy.elements().removeClass("cascade-node cascade-origin cascade-edge");
      });
      cascadeTimeoutRef.current = null;
    }, CASCADE_TTL_MS);
  }, [emergentEvents]);

  // Cleanup cascade timeout on unmount
  useEffect(() => {
    return () => {
      if (cascadeTimeoutRef.current !== null) {
        clearTimeout(cascadeTimeoutRef.current);
      }
    };
  }, []);

  // --- Zoom controls ---
  const handleZoomIn = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);

  const handleZoomOut = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() / 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);

  const handleFit = useCallback(() => {
    cyRef.current?.fit(undefined, 40);
  }, []);

  // Determine if a cascade is currently active (for badge glow)
  const cascadeActive = emergentEvents.length > 0 &&
    (emergentEvents[emergentEvents.length - 1].event_type.toLowerCase().includes("cascade") ||
     emergentEvents[emergentEvents.length - 1].event_type.toLowerCase().includes("viral"));

  return (
    <div
      data-testid="graph-panel"
      aria-label="Social network graph visualization"
      className="relative w-full h-full overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse at center, #0f172a 0%, #020617 100%)",
      }}
    >
      {/* Cytoscape canvas container */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Title Overlay — top-left */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <h2 className="text-lg font-bold text-white">AI Social World</h2>
        <p className="text-xs text-white/60">
          MiroFish Engine — {nodeCount} Active Agents · Force-Directed Graph
        </p>
      </div>

      {/* Zoom Controls — top-right */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1">
        <GraphButton
          testId="zoom-in-btn"
          icon={<ZoomIn className="w-4 h-4" />}
          label="Zoom in"
          onClick={handleZoomIn}
        />
        <GraphButton
          testId="zoom-out-btn"
          icon={<ZoomOut className="w-4 h-4" />}
          label="Zoom out"
          onClick={handleZoomOut}
        />
        <GraphButton
          testId="zoom-maximize-btn"
          icon={<Maximize2 className="w-4 h-4" />}
          label="Fit to screen"
          onClick={handleFit}
        />
      </div>

      {/* Cascade Badge — glows golden when a cascade/viral event is active */}
      <div data-testid="cascade-badge" className="absolute bottom-20 left-6 z-10 pointer-events-none">
        {emergentEvents.length > 0 && (
          <span
            className={`inline-flex items-center gap-1.5 text-[11px] font-semibold text-[var(--sentiment-positive)] bg-green-950/60 border border-green-800/40 px-2.5 py-1 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.3)] ${cascadeActive ? "cascade-badge-active" : ""}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--sentiment-positive)] animate-pulse-dot" />
            {(emergentEvents[emergentEvents.length - 1]?.event_type ?? "event").replace("_", " ")} detected
          </span>
        )}
      </div>

      {/* Tooltip overlay */}
      {hoverInfo && (
        <div
          className="absolute z-20 pointer-events-none px-2.5 py-1.5 rounded-md bg-black/80 border border-white/10 backdrop-blur-sm"
          style={{
            left: hoverInfo.x + 12,
            top: hoverInfo.y - 10,
          }}
        >
          <p className="text-xs font-semibold text-white">{hoverInfo.label}</p>
          <p className="text-[10px] text-white/60">
            {hoverInfo.community} · {hoverInfo.type}
          </p>
          <p className="text-[10px] text-white/60">
            Influence: {hoverInfo.influenceScore.toFixed(2)}
          </p>
          <p className="text-[10px] text-white/60">
            Connections: {hoverInfo.connections}
          </p>
        </div>
      )}

      {/* Selected agent info */}
      {selectedAgent && (
        <div className="absolute top-14 left-4 z-10 pointer-events-none">
          <span className="text-[11px] font-mono text-[var(--sentiment-positive)] bg-green-950/40 px-2 py-0.5 rounded">
            Selected: {selectedAgent}
          </span>
        </div>
      )}

      {/* Legend — bottom-left */}
      <div data-testid="network-legend" className="absolute bottom-4 left-4 z-10 bg-black/40 rounded-lg p-3 backdrop-blur-sm">
        <div className="flex flex-col gap-1.5">
          {legendItems.map((item) => {
            const commId = COMMUNITIES.find((c) => c.name === item.name)?.id ?? item.name;
            const isHighlighted = highlightedCommunity === commId;
            return (
              <button
                key={item.name}
                onClick={() => setHighlightedCommunity(isHighlighted ? null : commId)}
                title={isHighlighted ? `Clear highlight` : `Highlight ${item.name}`}
                className={`flex items-center gap-2 rounded px-1 transition-opacity cursor-pointer text-left ${
                  highlightedCommunity && !isHighlighted ? "opacity-40" : "opacity-100"
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-[11px] text-white/80 w-12">
                  {item.name}
                </span>
                <span className="text-[10px] text-white/50 font-mono">
                  {item.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Performance Indicator — bottom-right (GAP-5) */}
      <div data-testid="status-overlay" className="absolute bottom-2 right-2 z-10 pointer-events-none">
        <span className="text-[10px] font-mono text-[var(--muted-foreground,rgba(255,255,255,0.4))]">
          {nodeCount} nodes · {edgeCount} edges · {fps} FPS
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function GraphButton({
  icon,
  label,
  onClick,
  testId,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  testId?: string;
}) {
  return (
    <button
      data-testid={testId}
      title={label}
      aria-label={label}
      onClick={onClick}
      className="w-8 h-8 flex items-center justify-center rounded-md bg-[var(--card)]/10 text-white/70 hover:bg-[var(--card)]/20 hover:text-white transition-colors"
    >
      {icon}
    </button>
  );
}
