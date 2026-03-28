/**
 * EgoGraph -- Ego-network graph visualization for a single agent.
 * @spec docs/spec/ui/UI_11_AGENT_CONNECTIONS.md#ego-network-graph-area
 *
 * Uses Cytoscape.js with concentric layout: center node (the agent)
 * surrounded by connected nodes colored by community.
 */
import { useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, Filter } from "lucide-react";

// ---------------------------------------------------------------------------
// Community palette (must match GraphPanel & DESIGN.md)
// ---------------------------------------------------------------------------
const COMMUNITY_COLOR: Record<string, string> = {
  Alpha: "#3b82f6",
  Beta: "#22c55e",
  Gamma: "#f97316",
  Delta: "#a855f7",
  Bridge: "#ef4444",
};

// ---------------------------------------------------------------------------
// Mock ego-network data
// ---------------------------------------------------------------------------
interface EgoNode {
  data: {
    id: string;
    label: string;
    community: string;
    isCenter: boolean;
    trust: number;
    influence: number;
  };
}

interface EgoEdge {
  data: {
    id: string;
    source: string;
    target: string;
    trust: number;
  };
}

function generateEgoData(centerId: string): { nodes: EgoNode[]; edges: EgoEdge[] } {
  const nodes: EgoNode[] = [];
  const edges: EgoEdge[] = [];

  // Center node
  nodes.push({
    data: {
      id: centerId,
      label: `Agent #${centerId}`,
      community: "Alpha",
      isCenter: true,
      trust: 1,
      influence: 0.98,
    },
  });

  const connections = [
    { id: "1043", community: "Alpha", trust: 0.92, influence: 0.85 },
    { id: "4214", community: "Beta", trust: 0.87, influence: 0.72 },
    { id: "0891", community: "Alpha", trust: 0.84, influence: 0.68 },
    { id: "2301", community: "Gamma", trust: 0.79, influence: 0.61 },
    { id: "7782", community: "Delta", trust: 0.75, influence: 0.55 },
    { id: "0012", community: "Bridge", trust: 0.73, influence: 0.90 },
    { id: "5567", community: "Beta", trust: 0.71, influence: 0.48 },
    { id: "3344", community: "Alpha", trust: 0.68, influence: 0.52 },
    { id: "9102", community: "Gamma", trust: 0.65, influence: 0.44 },
    { id: "6655", community: "Delta", trust: 0.62, influence: 0.39 },
    { id: "1199", community: "Alpha", trust: 0.58, influence: 0.35 },
    { id: "8800", community: "Beta", trust: 0.55, influence: 0.31 },
    { id: "4410", community: "Gamma", trust: 0.52, influence: 0.28 },
    { id: "3378", community: "Alpha", trust: 0.48, influence: 0.25 },
    { id: "2200", community: "Delta", trust: 0.45, influence: 0.22 },
    { id: "7711", community: "Bridge", trust: 0.42, influence: 0.78 },
    { id: "5500", community: "Beta", trust: 0.39, influence: 0.19 },
    { id: "6644", community: "Gamma", trust: 0.35, influence: 0.16 },
    { id: "9933", community: "Alpha", trust: 0.32, influence: 0.14 },
  ];

  for (const conn of connections) {
    nodes.push({
      data: {
        id: conn.id,
        label: `Agent #${conn.id}`,
        community: conn.community,
        isCenter: false,
        trust: conn.trust,
        influence: conn.influence,
      },
    });
    edges.push({
      data: {
        id: `e-${centerId}-${conn.id}`,
        source: centerId,
        target: conn.id,
        trust: conn.trust,
      },
    });
  }

  // A few inter-connection edges for visual interest
  const interEdges: [string, string, number][] = [
    ["1043", "0891", 0.6],
    ["1043", "3344", 0.5],
    ["4214", "5567", 0.7],
    ["2301", "9102", 0.55],
    ["0012", "7711", 0.8],
    ["7782", "6655", 0.45],
  ];
  for (const [src, tgt, trust] of interEdges) {
    edges.push({
      data: {
        id: `e-${src}-${tgt}`,
        source: src,
        target: tgt,
        trust,
      },
    });
  }

  return { nodes, edges };
}

// ---------------------------------------------------------------------------
// Cytoscape style sheet
// ---------------------------------------------------------------------------
function nodeColor(ele: cytoscape.NodeSingular): string {
  const community = ele.data("community") as string;
  return COMMUNITY_COLOR[community] ?? "#888888";
}

const CY_STYLE: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      width: 8,
      height: 8,
      "background-color": nodeColor as unknown as string,
      label: "",
      "border-width": 0,
      "overlay-opacity": 0,
    },
  },
  {
    selector: 'node[?isCenter]',
    style: {
      width: 20,
      height: 20,
      "border-width": 1.5,
      "border-color": "#ffffff",
      "shadow-blur": 16,
      "shadow-color": nodeColor as unknown as string,
      "shadow-opacity": 0.6,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      label: "data(label)",
      "font-size": 8,
      color: "#ffffff",
      "text-valign": "top",
      "text-margin-y": -8,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1,
      "line-color": "#ffffff",
      opacity: 0.12,
      "curve-style": "haystack",
    },
  },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface EgoGraphProps {
  agentId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function EgoGraph({ agentId }: EgoGraphProps) {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const cyRef = useRef<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const { nodes, edges } = generateEgoData(agentId);

    const cy = cytoscape({
      container: containerRef.current,
      elements: { nodes, edges },
      style: CY_STYLE,
      layout: {
        name: "concentric",
        concentric(node: cytoscape.NodeSingular) {
          return node.data("isCenter") ? 10 : 1;
        },
        levelWidth() {
          return 1;
        },
        minNodeSpacing: 30,
        fit: true,
        padding: 30,
        animate: false,
      } as cytoscape.ConcentricLayoutOptions,
      minZoom: 0.3,
      maxZoom: 5,
      wheelSensitivity: 0.3,
    });

    // Apply trust-based edge opacity
    cy.edges().forEach((edge) => {
      const trust = edge.data("trust") as number;
      edge.style("opacity", Math.max(0.06, trust * 0.4));
    });

    // Click: navigate to agent detail (not center node)
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      if (node.data("isCenter")) return;
      navigateRef.current(`/agents/${node.data("id")}`);
    });

    // Hover: enlarge node
    cy.on("mouseover", "node", (evt: EventObject) => {
      const node = evt.target;
      if (!node.data("isCenter")) {
        node.style({ width: 12, height: 12 });
      }
      containerRef.current!.style.cursor = node.data("isCenter")
        ? "default"
        : "pointer";
    });

    cy.on("mouseout", "node", (evt: EventObject) => {
      const node = evt.target;
      if (!node.data("isCenter")) {
        node.style({ width: 8, height: 8 });
      }
      containerRef.current!.style.cursor = "default";
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [agentId]);

  // --- Zoom controls ---
  const handleZoomIn = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * 1.3,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  }, []);

  const handleZoomOut = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() / 1.3,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  }, []);

  const handleFit = useCallback(() => {
    cyRef.current?.fit(undefined, 30);
  }, []);

  return (
    <div className="relative w-full h-full">
      {/* Cytoscape canvas */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Toolbar -- top-right */}
      <div className="absolute top-3 right-3 z-10 flex gap-1">
        <ToolbarButton
          icon={<ZoomIn className="w-4 h-4" />}
          label="Zoom in"
          onClick={handleZoomIn}
        />
        <ToolbarButton
          icon={<ZoomOut className="w-4 h-4" />}
          label="Zoom out"
          onClick={handleZoomOut}
        />
        <ToolbarButton
          icon={<Maximize2 className="w-4 h-4" />}
          label="Fit to view"
          onClick={handleFit}
        />
        <ToolbarButton
          icon={<Filter className="w-4 h-4" />}
          label="Filter by community"
          onClick={() => {
            /* TODO: community filter popover */
          }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component
// ---------------------------------------------------------------------------
function ToolbarButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <button
      title={label}
      aria-label={label}
      onClick={onClick}
      className="w-8 h-8 flex items-center justify-center rounded-md bg-white/10 text-white/70 hover:bg-white/20 hover:text-white transition-colors"
    >
      {icon}
    </button>
  );
}
