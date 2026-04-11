/**
 * API request/response type definitions — extracted from api/client.ts.
 *
 * SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#4.1
 *
 * These types define the contract between frontend and backend API.
 * Domain types (SimulationRun, StepResult, etc.) live in types/simulation.ts.
 */

// ── Simulation ────────────────────────────────────────────────────────

export interface CommunityConfigInput {
  id: string;
  name: string;
  size: number;
  agent_type: string;
  personality_profile: {
    openness: number;
    skepticism: number;
    trend_following: number;
    brand_loyalty: number;
    social_influence: number;
  };
}

export interface CreateSimulationConfig {
  name: string;
  description?: string;
  project_id?: string;
  campaign: {
    name: string;
    budget?: number;
    channels: string[];
    message: string;
    target_communities: string[];
    controversy?: number;
    novelty?: number;
    utility?: number;
  };
  communities?: CommunityConfigInput[];
  max_steps?: number;
  default_llm_provider?: string;
  random_seed?: number;
  slm_llm_ratio?: number;
  slm_model?: string;
  budget_usd?: number;
}

// ── Settings ──────────────────────────────────────────────────────────

export interface SettingsLlm {
  default_provider: string;
  ollama_base_url: string;
  ollama_default_model: string;
  slm_model: string;
  ollama_embed_model: string;
  anthropic_model: string;
  anthropic_api_key_set: boolean;
  openai_model: string;
  openai_api_key_set: boolean;
}

export interface SettingsSimulation {
  slm_llm_ratio: number;
  llm_tier3_ratio: number;
  llm_cache_ttl: number;
}

export interface SettingsResponse {
  llm: SettingsLlm;
  simulation: SettingsSimulation;
}

export interface SettingsUpdateRequest {
  llm?: Partial<{
    default_provider: string;
    ollama_base_url: string;
    ollama_default_model: string;
    slm_model: string;
    ollama_embed_model: string;
    anthropic_api_key: string;
    anthropic_model: string;
    openai_api_key: string;
    openai_model: string;
  }>;
  simulation?: Partial<SettingsSimulation>;
}

// ── Agents ────────────────────────────────────────────────────────────

export interface AgentSummary {
  agent_id: string;
  community_id: string;
  agent_type: string;
  action: string;
  adopted: boolean;
  influence_score: number;
  belief: number;
}

export interface MemoryRecord {
  memory_type: string;
  content: string;
  timestamp: number;
  importance: number;
  source_agent_id?: string;
}

export interface AgentDetail extends AgentSummary {
  personality: Record<string, number>;
  emotion: Record<string, number>;
  memories: MemoryRecord[];
}

// ── Projects / Scenarios ──────────────────────────────────────────────

export interface ProjectSummary {
  project_id: string;
  name: string;
  description: string;
  status: string;
  scenario_count: number;
  created_at: string | null;
}

export interface ScenarioInfo {
  scenario_id: string;
  name: string;
  description: string;
  status: string;
  simulation_id: string | null;
  config: Record<string, unknown>;
  created_at: string | null;
}

export interface ProjectDetail extends ProjectSummary {
  scenarios: ScenarioInfo[];
}

// ── Communities ────────────────────────────────────────────────────────

export interface CommunityInfo {
  community_id: string;
  name: string;
  size: number;
  adoption_rate: number;
  mean_belief: number;
  sentiment_variance: number;
  dominant_action: string;
}

// ── Threads ───────────────────────────────────────────────────────────

export interface ThreadSummary {
  thread_id: string;
  topic: string;
  participant_count: number;
  message_count: number;
  avg_sentiment: number;
}

export interface ThreadMessage {
  message_id: string;
  agent_id: string;
  community_id: string;
  stance: 'Progressive' | 'Conservative' | 'Neutral';
  content: string;
  reactions: { agree: number; disagree: number; nuanced: number };
  is_reply: boolean;
  reply_to_id: string | null;
}

export interface ThreadDetail extends ThreadSummary {
  messages: ThreadMessage[];
}

// ── Community Templates ───────────────────────────────────────────────

export interface CommunityTemplate {
  template_id: string;
  name: string;
  agent_type: string;
  default_size: number;
  description: string;
  personality_profile: Record<string, number>;
}

export interface CommunityTemplateInput {
  name: string;
  agent_type: string;
  default_size: number;
  description?: string;
  personality_profile?: Record<string, number>;
}

// ── Run All ───────────────────────────────────────────────────────────

export interface RunAllReport {
  simulation_id: string;
  status: string;
  total_steps: number;
  final_adoption_rate: number;
  final_mean_sentiment: number;
  community_summary: Array<Record<string, unknown>>;
  emergent_events_count: number;
  duration_ms: number;
}

// ── Network ───────────────────────────────────────────────────────────

export interface CytoscapeGraph {
  nodes: Array<{ data: Record<string, unknown> }>;
  edges: Array<{ data: Record<string, unknown> }>;
  total_nodes?: number;
  total_edges?: number;
}

export interface NetworkMetrics {
  clustering_coefficient: number;
  avg_path_length: number;
  modularity: number;
  density: number;
  total_nodes: number;
  total_edges: number;
}
