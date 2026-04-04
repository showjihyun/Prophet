/**
 * FactionMapView — Faction-based opinion visualization using Cytoscape.js.
 * @spec docs/spec/ui/UI_13_SCENARIO_OPINIONS.md#faction-view
 *
 * Positions communities along a horizontal belief axis:
 *   Left (negative belief) ← → Right (positive belief)
 * Node size = agent count. Node color = community color.
 * Edges connect communities with shared opinion flow (propagation).
 * Vertical axis spreads communities for readability.
 */
import { useEffect, useRef, useMemo } from "react";
import cytoscape, { type Core } from "cytoscape";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FactionCommunity {
  community_id: string;
  community_name: string;
  agent_count: number;
  avg_sentiment: number;
  conversation_count: number;
  dominant_stance: "positive" | "negative" | "mixed";
  dominant_pct: number;
  color: string;
}

interface FactionMapViewProps {
  communities: FactionCommunity[];
  onCommunityClick?: (communityId: string) => void;
}

// ---------------------------------------------------------------------------
// Color helpers
// ---------------------------------------------------------------------------

const CSS_VAR_TO_HEX: Record<string, string> = {
  "var(--community-alpha)": "#3b82f6",
  "var(--community-beta)": "#22c55e",
  "var(--community-gamma)": "#f97316",
  "var(--community-delta)": "#a855f7",
  "var(--community-bridge)": "#ef4444",
  "var(--muted-foreground)": "#94a3b8",
};

function resolveColor(cssVar: string): string {
  return CSS_VAR_TO_HEX[cssVar] ?? cssVar;
}

function stanceColor(sentiment: number): string {
  if (sentiment > 0.1) return "#22c55e";
  if (sentiment < -0.1) return "#ef4444";
  return "#94a3b8";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FactionMapView({ communities, onCommunityClick }: FactionMapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Build Cytoscape elements from community data
  const elements = useMemo(() => {
    if (communities.length === 0) return { nodes: [], edges: [] };

    // Nodes: one per community, positioned by sentiment on X axis
    const nodes = communities.map((c, idx) => {
      const size = Math.max(40, Math.min(120, Math.sqrt(c.agent_count) * 2));
      // X position: sentiment -1..+1 mapped to 100..900
      const x = 100 + ((c.avg_sentiment + 1) / 2) * 800;
      // Y position: spread vertically
      const y = 150 + (idx % 3) * 200 + (idx > 2 ? 100 : 0);

      return {
        data: {
          id: c.community_id,
          label: c.community_name.replace("Community ", ""),
          agentCount: c.agent_count,
          sentiment: c.avg_sentiment,
          stance: c.dominant_stance,
          stancePct: c.dominant_pct,
          conversations: c.conversation_count,
          color: resolveColor(c.color),
          size,
        },
        position: { x, y },
      };
    });

    // Edges: connect communities that share opinion flow
    // Thicker edge = more conversations between them (simulated by overlapping stance)
    const edges: { data: { id: string; source: string; target: string; weight: number } }[] = [];
    for (let i = 0; i < communities.length; i++) {
      for (let j = i + 1; j < communities.length; j++) {
        const a = communities[i];
        const b = communities[j];
        // Weight based on how similar their stance is (closer belief = stronger connection)
        const beliefDist = Math.abs(a.avg_sentiment - b.avg_sentiment);
        const weight = Math.max(0, 1 - beliefDist);
        if (weight > 0.2) {
          edges.push({
            data: {
              id: `${a.community_id}-${b.community_id}`,
              source: a.community_id,
              target: b.community_id,
              weight,
            },
          });
        }
      }
    }

    return { nodes, edges };
  }, [communities]);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || elements.nodes.length === 0) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...elements.nodes, ...elements.edges],
      layout: { name: "preset" },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
      style: [
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            "background-color": "data(color)",
            "background-opacity": 0.85,
            "border-width": 3,
            "border-color": (ele: { data: (key: string) => number }) =>
              stanceColor(ele.data("sentiment")),
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "12px",
            "font-weight": "600",
            color: "#ffffff",
            "text-outline-width": 2,
            "text-outline-color": "data(color)",
          } as Record<string, unknown>,
        },
        {
          selector: "edge",
          style: {
            width: (ele: { data: (key: string) => number }) =>
              Math.max(1, ele.data("weight") * 6),
            "line-color": "#64748b",
            "line-opacity": (ele: { data: (key: string) => number }) =>
              0.2 + ele.data("weight") * 0.4,
            "curve-style": "bezier",
          } as Record<string, unknown>,
        },
        {
          selector: "node:active",
          style: {
            "overlay-opacity": 0.1,
          } as Record<string, unknown>,
        },
      ],
    });

    cyRef.current = cy;

    // Click handler
    cy.on("tap", "node", (evt) => {
      const nodeId = evt.target.id();
      onCommunityClick?.(nodeId);
    });

    // Hover: enlarge + show detail
    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      node.animate({ style: { width: node.data("size") * 1.15, height: node.data("size") * 1.15 } }, { duration: 150 });
    });
    cy.on("mouseout", "node", (evt) => {
      const node = evt.target;
      node.animate({ style: { width: node.data("size"), height: node.data("size") } }, { duration: 150 });
    });

    // Fit view
    cy.fit(undefined, 30);

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, onCommunityClick]);

  return (
    <div className="relative rounded-xl border border-[var(--border)] bg-[var(--card)] overflow-hidden" style={{ minHeight: 500 }}>
      {/* Axis labels */}
      <div className="absolute top-3 left-0 right-0 flex justify-between px-6 z-10 pointer-events-none">
        <span className="text-xs font-medium px-2 py-0.5 rounded bg-[var(--destructive)]/10 text-[var(--destructive)]">
          Negative Belief
        </span>
        <span className="text-xs font-medium text-[var(--muted-foreground)]">
          Neutral
        </span>
        <span className="text-xs font-medium px-2 py-0.5 rounded bg-[var(--sentiment-positive)]/10 text-[var(--sentiment-positive)]">
          Positive Belief
        </span>
      </div>

      {/* Gradient axis line */}
      <div className="absolute top-10 left-6 right-6 h-0.5 z-10 pointer-events-none rounded-full"
        style={{ background: "linear-gradient(to right, #ef4444, #94a3b8, #22c55e)" }}
      />

      {/* Cytoscape container */}
      <div ref={containerRef} className="w-full" style={{ height: 500 }} />

      {/* Legend */}
      <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1 bg-[var(--card)]/90 backdrop-blur rounded-lg px-3 py-2 border border-[var(--border)]">
        <span className="text-[10px] font-medium text-[var(--muted-foreground)] uppercase tracking-wide">Legend</span>
        <div className="flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[var(--sentiment-positive)]" /> Positive
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[#94a3b8]" /> Mixed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[var(--destructive)]" /> Negative
          </span>
        </div>
        <span className="text-[10px] text-[var(--muted-foreground)]">Node size = agent count. Border = belief stance.</span>
      </div>

      {/* Stat overlay */}
      <div className="absolute bottom-3 right-3 z-10 text-[10px] text-[var(--muted-foreground)] bg-[var(--card)]/90 backdrop-blur rounded px-2 py-1 border border-[var(--border)]">
        {communities.length} factions . Cytoscape.js
      </div>
    </div>
  );
}
