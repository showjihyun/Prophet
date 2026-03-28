/**
 * LLM dashboard types.
 * @spec docs/spec/05_LLM_SPEC.md
 */

export interface LLMStats {
  total_calls: number;
  cached_calls: number;
  provider_breakdown: Record<string, number>;
  avg_latency_ms: number;
  total_tokens: number;
  tier_breakdown: Record<string, number>;
}

export interface LLMCallLog {
  call_id: string;
  simulation_id: string;
  agent_id: string;
  step: number;
  provider: string;
  model: string;
  latency_ms: number;
  cached: boolean;
  tier: number;
  error: string | null;
}
