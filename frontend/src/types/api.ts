/**
 * API request/response type definitions — extracted from api/client.ts.
 *
 * SPEC: docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#4.1
 *
 * These types define the contract between frontend and backend API.
 * Domain types (SimulationRun, StepResult, etc.) live in types/simulation.ts.
 */

// ── Simulation ────────────────────────────────────────────────────────

/**
 * The shape ``/api/v1/simulations`` accepts for a community entry.
 *
 * ``personality_profile`` is **optional and partial** because:
 *   - The backend fills any missing trait with a 0.5 default at agent
 *     generation time (see ``orchestrator.create_simulation`` and the
 *     ``_trait`` helper in ``app/engine/simulation/orchestrator.py``).
 *   - The frontend API client already documents it as optional
 *     (``src/api/client.ts:130,132``).
 *   - ``communitySimilarity.personalityVector`` defensively uses
 *     ``c.personality_profile ?? {}`` and falls back to 0.5 per trait.
 *
 * Treating it as required with all five fields forced every caller to
 * pass the full profile, including tests that intentionally exercise
 * the "missing profile" fallback. The runtime shape was always partial.
 */
export interface CommunityConfigInput {
  id: string;
  name: string;
  size: number;
  agent_type: string;
  personality_profile?: Partial<{
    openness: number;
    skepticism: number;
    trend_following: number;
    brand_loyalty: number;
    social_influence: number;
  }>;
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
  // Gemini — real adapter at backend/app/llm/gemini_client.py
  gemini_model: string;
  gemini_embed_model: string;
  gemini_api_key_set: boolean;
  // vLLM — self-hosted high-throughput inference server, alternative to Ollama
  vllm_base_url: string;
  vllm_model: string;
  vllm_max_concurrent: number;
  // Chinese Top 3 (2026, OpenAI-compatible)
  deepseek_base_url: string;
  deepseek_model: string;
  deepseek_api_key_set: boolean;
  qwen_base_url: string;
  qwen_model: string;
  qwen_api_key_set: boolean;
  moonshot_base_url: string;
  moonshot_model: string;
  moonshot_api_key_set: boolean;
  glm_base_url: string;
  glm_model: string;
  glm_api_key_set: boolean;
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
    gemini_api_key: string;
    gemini_model: string;
    gemini_embed_model: string;
    vllm_base_url: string;
    vllm_model: string;
    vllm_max_concurrent: number;
    deepseek_api_key: string;
    deepseek_base_url: string;
    deepseek_model: string;
    qwen_api_key: string;
    qwen_base_url: string;
    qwen_model: string;
    moonshot_api_key: string;
    moonshot_base_url: string;
    moonshot_model: string;
    glm_api_key: string;
    glm_base_url: string;
    glm_model: string;
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
  /**
   * Human-readable community name resolved by the backend (e.g. "skeptics").
   * ``null`` when the backend couldn't resolve one — the frontend should
   * fall back to ``community_id`` for display.
   */
  community_name?: string | null;
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

// ── Community Opinion (EliteLLM synthesis) ────────────────────────────

export interface CommunityOpinionTheme {
  theme: string;
  weight: number;
  evidence_step: number;
}

export interface CommunityOpinionDivision {
  faction: string;
  share: number;
  concerns: string[];
}

export interface CommunityOpinionKeyQuote {
  agent_id: string;
  content: string;
  step: number;
}

export interface CommunityOpinion {
  opinion_id: string;
  simulation_id: string;
  community_id: string;
  step: number;
  summary: string;
  sentiment_trend: 'rising' | 'stable' | 'polarising' | 'collapsing' | string;
  themes: CommunityOpinionTheme[];
  divisions: CommunityOpinionDivision[];
  dominant_emotions: string[];
  key_quotes: CommunityOpinionKeyQuote[];
  source_step_count: number;
  source_agent_count: number;
  llm_provider: string;
  llm_model: string;
  is_fallback_stub: boolean;
}

export interface OverallOpinion {
  overall: CommunityOpinion;
  communities: CommunityOpinion[];
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

// ── Monte Carlo (SPEC 29) ─────────────────────────────────────────────

export interface RunSummaryItem {
  run_id: number;
  final_adoption: number;
  viral_detected: boolean;
  steps_completed: number;
}

export interface MonteCarloResponse {
  simulation_id: string;
  n_runs: number;
  viral_probability: number;
  expected_reach: number;
  p5_reach: number;
  p50_reach: number;
  p95_reach: number;
  community_adoption: Record<string, number>;
  run_summaries: RunSummaryItem[];
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
