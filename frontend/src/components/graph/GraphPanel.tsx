/**
 * GraphPanel — AI Social World Graph Engine (Zone 2 Center).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-center-ai-social-world-graph-engine
 * @spec docs/spec/ui/DESIGN.md#5-graph-engine-visual-spec
 *
 * Cytoscape.js canvas renderer with force-directed layout,
 * community-colored nodes, and interactive selection.
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { apiClient, type CytoscapeGraph } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";

// ---------------------------------------------------------------------------
// Community palette (must match CSS vars & DESIGN.md §5)
// ---------------------------------------------------------------------------
const COMMUNITIES = [
  { id: "A", name: "Alpha", color: "#3b82f6", size: 50 },
  { id: "B", name: "Beta", color: "#22c55e", size: 40 },
  { id: "C", name: "Gamma", color: "#f97316", size: 35 },
  { id: "D", name: "Delta", color: "#a855f7", size: 25 },
  { id: "E", name: "Bridge", color: "#ef4444", size: 10 },
] as const;

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
  navigateRef.current = navigate;
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

  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);

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

      // Performance options (DESIGN.md §5)
      textureOnViewport: true,
      hideEdgesOnViewport: true,
      pixelRatio: 1,

      // Interaction
      minZoom: 0.2,
      maxZoom: 5,
      // wheelSensitivity removed — Cytoscape default (1.0) used
    });

    setNodeCount(cy.nodes().length);
    setEdgeCount(cy.edges().length);

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

      {/* Cascade Badge */}
      <div data-testid="cascade-badge" className="absolute bottom-20 left-6 z-10 pointer-events-none">
        {emergentEvents.length > 0 && (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-[var(--sentiment-positive)] bg-green-950/60 border border-green-800/40 px-2.5 py-1 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.3)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--sentiment-positive)] animate-pulse-dot" />
            {emergentEvents[emergentEvents.length - 1].event_type.replace("_", " ")} detected
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
          {legendItems.map((item) => (
            <div key={item.name} className="flex items-center gap-2">
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
            </div>
          ))}
        </div>
      </div>

      {/* Status Bar — bottom-right */}
      <div data-testid="status-overlay" className="absolute bottom-4 right-4 z-10 pointer-events-none">
        <span className="text-[11px] font-mono text-white/40">
          60 FPS · {nodeCount} nodes · {edgeCount} edges · WebGL
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
