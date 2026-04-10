/**
 * EgoGraph -- Ego-network graph visualization for a single agent.
 * @spec docs/spec/ui/UI_11_AGENT_CONNECTIONS.md#ego-network-graph-area
 *
 * Uses Cytoscape.js with concentric layout: center node (the agent)
 * surrounded by connected nodes colored by community.
 *
 * Real-data-only: fetches the simulation's network graph from the API
 * and extracts the ego subgraph for the given agent. No mock data.
 */
import { useEffect, useRef, useCallback, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, Filter, X } from "lucide-react";
import { COMMUNITY_PALETTE } from "@/config/constants";
import type { CytoscapeGraph } from "../../api/client";
import { useSimulationStore } from "../../store/simulationStore";
import { useNetwork } from "../../api/queries";

const COMMUNITY_COLOR: Record<string, string> = { ...COMMUNITY_PALETTE };

// --------------------------------------------------------------------------- //
// Types                                                                       //
// --------------------------------------------------------------------------- //

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

// --------------------------------------------------------------------------- //
// Build ego subgraph from real network data                                   //
// --------------------------------------------------------------------------- //

function buildEgoFromNetwork(
  graph: CytoscapeGraph,
  agentId: string,
): { nodes: EgoNode[]; edges: EgoEdge[] } | null {
  // 1. Find the center node by agent_id (UUID).
  const centerNode = graph.nodes.find(
    (n) => String(n.data.agent_id) === agentId,
  );
  if (!centerNode) return null;

  const centerId = String(centerNode.data.id);
  const centerCommunity = String(centerNode.data.community ?? "Unknown");

  // 2. Find all edges touching the center node.
  const touchingEdges = graph.edges.filter(
    (e) =>
      String(e.data.source) === centerId || String(e.data.target) === centerId,
  );

  // 3. Collect neighbor node ids.
  const neighborIds = new Set<string>();
  for (const e of touchingEdges) {
    const src = String(e.data.source);
    const tgt = String(e.data.target);
    if (src !== centerId) neighborIds.add(src);
    if (tgt !== centerId) neighborIds.add(tgt);
  }

  // 4. Build node list.
  const nodes: EgoNode[] = [
    {
      data: {
        id: centerId,
        label: String(centerNode.data.label ?? `Agent ${agentId.slice(0, 8)}`),
        community: centerCommunity,
        isCenter: true,
        trust: 1,
        influence: Number(centerNode.data.influence_score ?? 0.5),
      },
    },
  ];

  const nodeMap = new Map(graph.nodes.map((n) => [String(n.data.id), n]));
  for (const nid of neighborIds) {
    const n = nodeMap.get(nid);
    if (!n) continue;
    nodes.push({
      data: {
        id: nid,
        label: String(n.data.label ?? `Agent ${nid}`),
        community: String(n.data.community ?? "Unknown"),
        isCenter: false,
        trust: 0.5, // edges carry weight, used below
        influence: Number(n.data.influence_score ?? 0.3),
      },
    });
  }

  // 5. Build edge list.
  const edges: EgoEdge[] = touchingEdges.map((e) => ({
    data: {
      id: String(e.data.id ?? `e-${e.data.source}-${e.data.target}`),
      source: String(e.data.source),
      target: String(e.data.target),
      trust: Number(e.data.weight ?? 0.5),
    },
  }));

  // 6. Add a few inter-neighbor edges for visual density (max 10).
  // neighborIdArr removed — inter-edge iteration uses neighborIds Set directly
  const interEdgeSet = new Set<string>();
  for (const e of graph.edges) {
    const src = String(e.data.source);
    const tgt = String(e.data.target);
    if (neighborIds.has(src) && neighborIds.has(tgt) && interEdgeSet.size < 10) {
      const key = `${src}-${tgt}`;
      if (!interEdgeSet.has(key)) {
        interEdgeSet.add(key);
        edges.push({
          data: {
            id: `ie-${src}-${tgt}`,
            source: src,
            target: tgt,
            trust: Number(e.data.weight ?? 0.4),
          },
        });
      }
    }
  }
  // Also limit total neighbors displayed to 30 for readability.
  if (nodes.length > 31) {
    const kept = new Set(nodes.slice(0, 31).map((n) => n.data.id));
    return {
      nodes: nodes.filter((n) => kept.has(n.data.id)),
      edges: edges.filter(
        (e) => kept.has(e.data.source) && kept.has(e.data.target),
      ),
    };
  }

  return { nodes, edges };
}

// --------------------------------------------------------------------------- //
// Cytoscape style sheet                                                       //
// --------------------------------------------------------------------------- //

function nodeColor(ele: cytoscape.NodeSingular): string {
  const community = ele.data("community") as string;
  return COMMUNITY_COLOR[community] ?? "#888888";
}

const CY_STYLE: cytoscape.StylesheetStyle[] = [
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
    selector: "node[?isCenter]",
    style: {
      width: 20,
      height: 20,
      "border-width": 1.5,
      "border-color": "#ffffff",
      "underlay-color": nodeColor as unknown as string,
      "underlay-padding": 8,
      "underlay-opacity": 0.35,
      "underlay-shape": "ellipse",
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

// --------------------------------------------------------------------------- //
// Props                                                                       //
// --------------------------------------------------------------------------- //

interface EgoGraphProps {
  agentId: string;
}

const ALL_COMMUNITIES = Object.keys(COMMUNITY_COLOR);

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

export default function EgoGraph({ agentId }: EgoGraphProps) {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  useEffect(() => {
    navigateRef.current = navigate;
  });
  const cyRef = useRef<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const simulationId =
    useSimulationStore((s) => s.simulation?.simulation_id) ?? null;

  // Community filter
  const [filterOpen, setFilterOpen] = useState(false);
  const [visibleCommunities, setVisibleCommunities] = useState<Set<string>>(
    () => new Set(ALL_COMMUNITIES),
  );
  const filterRef = useRef<HTMLDivElement>(null);

  // Fetch network via TanStack Query (caches across re-renders)
  const networkQuery = useNetwork(simulationId);
  const loading = networkQuery.isLoading;

  // Derive empty state from network query data (no setState in effect)
  const empty = useMemo(() => {
    if (!simulationId) return true;
    const graph = networkQuery?.data as CytoscapeGraph | undefined;
    if (!graph) return !networkQuery?.isLoading;
    const egoData = buildEgoFromNetwork(graph, agentId);
    return !egoData || egoData.nodes.length === 0;
  }, [simulationId, networkQuery?.data, networkQuery?.isLoading, agentId]);

  useEffect(() => {
    if (!containerRef.current || !simulationId) {
      return;
    }
    // Derive ego graph data from cached network query (no setState in guard)
    const graph = networkQuery.data as CytoscapeGraph | undefined;
    let egoData: { nodes: EgoNode[]; edges: EgoEdge[] } | null = null;
    try {
      if (graph) {
        egoData = buildEgoFromNetwork(graph, agentId);
      }
    } catch {
      /* network not available */
    }

    if (!egoData || egoData.nodes.length === 0) {
      return;
    }

    // Mount Cytoscape instance with ego graph data
    {
      const cy = cytoscape({
        container: containerRef.current,
        elements: { nodes: egoData.nodes, edges: egoData.edges },
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
      });

      cy.edges().forEach((edge) => {
        const trust = edge.data("trust") as number;
        edge.style("opacity", Math.max(0.06, trust * 0.4));
      });

      cy.on("tap", "node", (evt: EventObject) => {
        const node = evt.target;
        if (node.data("isCenter")) return;
        // Navigate to the agent detail for the clicked neighbor.
        // Try to find the real agent_id from the original network node.
        navigateRef.current(`/agents/${node.data("id")}`);
      });

      cy.on("mouseover", "node", (evt: EventObject) => {
        const node = evt.target;
        if (!node.data("isCenter")) node.style({ width: 12, height: 12 });
        containerRef.current!.style.cursor = node.data("isCenter")
          ? "default"
          : "pointer";
      });

      cy.on("mouseout", "node", (evt: EventObject) => {
        const node = evt.target;
        if (!node.data("isCenter")) node.style({ width: 8, height: 8 });
        containerRef.current!.style.cursor = "default";
      });

      cyRef.current = cy;
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [agentId, simulationId, networkQuery.data]);

  // Community visibility filter
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().forEach((node) => {
      const community = node.data("community") as string;
      const visible = visibleCommunities.has(community);
      if (visible) {
        node.style({ opacity: 1, "z-index": 1 });
        node.connectedEdges().forEach((edge) => {
          const srcVis = visibleCommunities.has(
            edge.source().data("community") as string,
          );
          const tgtVis = visibleCommunities.has(
            edge.target().data("community") as string,
          );
          const trust = edge.data("trust") as number;
          edge.style({
            opacity: srcVis && tgtVis ? Math.max(0.06, trust * 0.4) : 0,
          });
        });
      } else {
        node.style({ opacity: 0.1, "z-index": 0 });
      }
    });
  }, [visibleCommunities]);

  // Close popover on outside click
  useEffect(() => {
    if (!filterOpen) return;
    const handler = (e: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [filterOpen]);

  const toggleCommunity = useCallback((community: string) => {
    setVisibleCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(community)) {
        if (next.size > 1) next.delete(community);
      } else {
        next.add(community);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setVisibleCommunities(new Set(ALL_COMMUNITIES));
  }, []);

  const isAllSelected = visibleCommunities.size === ALL_COMMUNITIES.length;

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

      {/* Loading */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-[var(--muted-foreground)]">
          Loading ego network…
        </div>
      )}

      {/* Empty state */}
      {!loading && empty && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-[var(--muted-foreground)]">
          No connections found for this agent.
        </div>
      )}

      {/* Toolbar -- top-right */}
      {!loading && !empty && (
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
          <div ref={filterRef} className="relative">
            <button
              title="Filter by community"
              aria-label="Filter by community"
              onClick={() => setFilterOpen((o) => !o)}
              className={[
                "w-8 h-8 flex items-center justify-center rounded-md transition-colors",
                filterOpen || !isAllSelected
                  ? "bg-[var(--accent)]/30 text-[var(--accent)] hover:bg-[var(--accent)]/40"
                  : "bg-[var(--card)]/10 text-white/70 hover:bg-[var(--card)]/20 hover:text-white",
              ].join(" ")}
            >
              <Filter className="w-4 h-4" />
              {!isAllSelected && (
                <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-[var(--accent)]" />
              )}
            </button>

            {filterOpen && (
              <div
                className="absolute top-10 right-0 z-20 w-48 rounded-lg border border-white/10 bg-[var(--card)] shadow-xl"
                role="dialog"
                aria-label="Community filter"
              >
                <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
                  <span className="text-xs font-semibold text-white/80 uppercase tracking-wide">
                    Communities
                  </span>
                  <button
                    onClick={() => setFilterOpen(false)}
                    className="text-white/40 hover:text-white/80 transition-colors"
                    aria-label="Close filter"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
                <div className="px-3 py-2 border-b border-white/5">
                  <label className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={isAllSelected}
                      onChange={selectAll}
                      className="w-3.5 h-3.5 rounded accent-[var(--accent)] cursor-pointer"
                    />
                    <span className="text-xs text-white/70 group-hover:text-white transition-colors">
                      All communities
                    </span>
                  </label>
                </div>
                <ul className="py-1" role="list">
                  {ALL_COMMUNITIES.map((community) => {
                    const color = COMMUNITY_COLOR[community];
                    const checked = visibleCommunities.has(community);
                    return (
                      <li key={community}>
                        <label className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-white/5 transition-colors">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleCommunity(community)}
                            className="w-3.5 h-3.5 rounded cursor-pointer"
                            style={{ accentColor: color }}
                          />
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: color }}
                          />
                          <span
                            className={[
                              "text-xs transition-colors",
                              checked ? "text-white/90" : "text-white/40",
                            ].join(" ")}
                          >
                            {community}
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
                {!isAllSelected && (
                  <div className="px-3 py-2 border-t border-white/5">
                    <button
                      onClick={selectAll}
                      className="text-xs text-[var(--accent)] hover:underline transition-colors"
                    >
                      Reset to all
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

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
      className="w-8 h-8 flex items-center justify-center rounded-md bg-[var(--card)]/10 text-white/70 hover:bg-[var(--card)]/20 hover:text-white transition-colors"
    >
      {icon}
    </button>
  );
}
