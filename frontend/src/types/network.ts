/**
 * Network graph types for Cytoscape.js visualization.
 * @spec docs/spec/07_FRONTEND_SPEC.md#graphpanel
 */

export interface AgentNodeData {
  id: string;
  label: string;
  community: string;
  agent_type: string;
  influence_score: number;
  emotion_state: {
    interest: number;
    trust: number;
    skepticism: number;
    excitement: number;
  };
  action: string;
  adopted: boolean;
}

export interface EdgeData {
  id: string;
  source: string;
  target: string;
  weight: number;
  is_bridge: boolean;
  sentiment_polarity?: number;
  message_strength?: number;
}

export interface CytoscapeNode {
  data: AgentNodeData;
}

export interface CytoscapeEdge {
  data: EdgeData;
}

export interface NetworkGraphData {
  nodes: CytoscapeNode[];
  edges: CytoscapeEdge[];
}
