/**
 * Simulation types — mirrors backend schemas.
 * @spec docs/spec/06_API_SPEC.md
 * @spec docs/spec/01_AGENT_SPEC.md
 */

export type SimulationStatus =
  | "created"
  | "configured"
  | "running"
  | "paused"
  | "completed"
  | "failed";

export type AgentAction =
  | "ignore" | "view" | "search"
  | "like" | "save" | "comment" | "share" | "repost"
  | "follow" | "unfollow"
  | "adopt"
  | "mute";

export interface AgentPersonality {
  openness: number;
  skepticism: number;
  trend_following: number;
  brand_loyalty: number;
  social_influence: number;
}

export interface AgentEmotion {
  interest: number;
  trust: number;
  skepticism: number;
  excitement: number;
}

export interface SimulationRun {
  simulation_id: string;
  /** Project that owns this simulation. Optional because legacy rows
   * persisted before project-scoping was wired up may be null. */
  project_id?: string | null;
  name: string;
  status: SimulationStatus;
  current_step: number;
  max_steps: number;
  created_at: string;
}

/** A single propagation event for graph animation (GAP-7). */
export interface PropagationPair {
  source: string;
  target: string;
  action: string;
  probability: number;
}

export interface StepResult {
  simulation_id: string;
  step: number;
  total_adoption: number;
  adoption_rate: number;
  diffusion_rate: number;
  mean_sentiment: number;
  sentiment_variance: number;
  community_metrics: Record<string, CommunityStepMetrics>;
  emergent_events: EmergentEvent[];
  action_distribution: Record<string, number>;
  propagation_pairs?: PropagationPair[];
  llm_calls_this_step: number;
  step_duration_ms: number;
}

export interface CommunityStepMetrics {
  community_id: string;
  adoption_count: number;
  adoption_rate: number;
  mean_belief: number;
  dominant_action: AgentAction;
  new_propagation_count: number;
}

export interface EmergentEvent {
  event_type: "viral_cascade" | "slow_adoption" | "polarization" | "collapse" | "echo_chamber";
  step: number;
  community_id: string | null;
  severity: number;
  description: string;
}

export interface TierDistribution {
  tier1_count: number;
  tier2_count: number;
  tier3_count: number;
  tier1_model: string;
  tier3_model: string;
  estimated_cost_per_step: number;
  estimated_latency_ms: number;
}

export interface EngineImpactReport {
  cost_efficiency: string;
  reasoning_depth: string;
  simulation_velocity: string;
  prediction_type: string;
}
