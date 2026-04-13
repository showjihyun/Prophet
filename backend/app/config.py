"""Application configuration — single source of truth for all tunables.
SPEC: docs/spec/00_ARCHITECTURE.md#environment-variables

All hardcoded constants across the codebase should reference ``settings``
instead of using magic numbers.  Values can be overridden via environment
variables or a ``.env`` file (Pydantic Settings auto-loads it).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://prophet:secret@localhost:5432/prophet"
    valkey_url: str = "valkey://localhost:6379/0"

    # ── LLM Providers ───────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    # Default Ollama model: llama3.1:8b.
    #
    # History:
    # - Round 7 briefly switched to gemma4:latest (9.6 GB, multimodal),
    #   but 0.20.x Ollama has a regression that crashes the llama
    #   runner on CPU inference.
    # - Round 8 moved back toward llama3.1:8b, but 5.6 GiB of RAM was
    #   too much for CPU-only inference on modest VRAM hosts. Round 8-5
    #   temporarily dropped to llama3.2:1b (~1.3 GB) so CPU mode stayed
    #   usable.
    # - Round 8-6 re-enables GPU inference via
    #   ``docker compose -f docker-compose.yml -f docker-compose.gpu.yml``.
    #   An RTX 4070-class card (12 GiB VRAM) runs llama3.1:8b at ~200+
    #   tok/s which is fast enough for every agent tick and makes the
    #   smaller 1B fallback unnecessary. 1B hallucinated narratives in
    #   the opinion synthesis even when given real numeric data; the 8B
    #   model stays anchored to the provided metrics. 1B is still the
    #   right choice for CPU-only laptops — override via the
    #   ``OLLAMA_DEFAULT_MODEL`` / ``SLM_MODEL`` env vars.
    ollama_default_model: str = "llama3.1:8b"
    slm_model: str = "llama3.1:8b"
    ollama_embed_model: str = "llama3.1:8b"
    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"
    gemini_api_key: str = ""
    gemini_default_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "models/text-embedding-004"
    vllm_base_url: str = ""  # empty = not configured
    vllm_default_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    vllm_max_concurrent: int = 64
    # ── Chinese LLM providers (2026 Top 3, OpenAI-compatible) ──
    # All three default to cloud endpoints; override base_url if you're
    # running a private gateway or need the mainland CN endpoint variant.
    # 2026-04 defaults — verified against each provider's docs:
    #   - DeepSeek V3.2 auto-aliased behind `deepseek-chat` (V4 launched
    #     2026-03, override model name manually if you want to pin it).
    #   - Qwen3-Max is the current flagship snapshot (2026-01-23).
    #   - Moonshot Kimi K2.5 shipped 2026-01 with 256K context + Agent
    #     Swarm; model ID is `kimi-k2.5`.
    #   - Zhipu GLM-5.1 released 2026-04, #1 on SWE-Bench Pro.
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-chat"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_default_model: str = "qwen3-max"
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.ai/v1"
    moonshot_default_model: str = "kimi-k2.5"
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    glm_default_model: str = "glm-5.1"

    # ── Distributed execution ───────────────────────────────────────────────
    ray_enabled: bool = False
    ray_address: str = "auto"
    ray_num_workers: int = 4

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── JWT Auth ────────────────────────────────────────────────────────────
    jwt_secret: str = "prophet-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_token_expire_hours: int = 24

    # ── Embedding ───────────────────────────────────────────────────────────
    embedding_dim: int = 768

    # ── LLM Inference Defaults ──────────────────────────────────────────────
    llm_default_max_tokens: int = 512
    llm_default_temperature: float = 0.7
    llm_timeout_seconds: float = 10.0
    llm_retry_count: int = 3
    llm_retry_delay_seconds: float = 1.0

    # ── LLM Engine Control ──────────────────────────────────────────────────
    default_llm_provider: str = "ollama"
    slm_llm_ratio: float = 0.5
    llm_tier3_ratio: float = 0.1
    llm_avg_cost_per_tier3_call: float = 0.003
    llm_tier1_latency_ms: float = 5.0
    llm_tier3_latency_ms: float = 500.0

    # ── LLM Cache / Gateway ─────────────────────────────────────────────────
    llm_cache_ttl: int = 3600
    llm_inmemory_cache_max_size: int = 1000
    llm_vector_similarity_threshold: float = 0.95
    llm_gateway_batch_size: int = 32
    llm_gateway_max_wait_ms: int = 100
    llm_budget_downgrade_threshold: float = 0.20
    llm_vector_cache_prompt_truncate: int = 2000
    slm_batch_size: int = 32

    # ── Tier Selection ──────────────────────────────────────────────────────
    tier_max_tier3_ratio: float = 0.10
    tier_max_tier2_ratio: float = 0.10
    tier_influencer_score_threshold: float = 0.7
    tier_critical_belief_threshold: float = 0.2
    tier_critical_exposure_count: int = 3
    tier_tier2_influence_threshold: float = 0.5
    tier_tier2_skeptic_threshold: float = 0.7

    # ── Simulation ──────────────────────────────────────────────────────────
    sim_max_concurrent: int = 3
    sim_max_simulations: int = 50
    sim_ttl_seconds: int = 86400
    sim_default_max_steps: int = 50
    sim_default_random_seed: int = 42
    sim_base_activation_rate: float = 0.10

    # ── Agent ───────────────────────────────────────────────────────────────
    agent_max_memories: int = 1000
    agent_max_personality_drift: float = 0.3
    memory_fallback_alpha: float = 0.6
    memory_fallback_beta: float = 0.25
    memory_fallback_gamma: float = 0.3
    memory_fallback_delta: float = 0.1

    # ── Orchestrator / Scalability ────────────────────────────────────────────
    community_batch_size: int = 32
    max_network_edges: int = 100_000

    # ── Cascade / Diffusion ─────────────────────────────────────────────────
    cascade_viral_threshold: float = 0.15
    cascade_slow_adoption_steps: int = 5
    cascade_polarization_variance: float = 0.4
    cascade_collapse_drop_rate: float = 0.20
    cascade_echo_chamber_ratio: float = 10.0
    sentiment_expert_alpha: float = 0.3
    bridge_trust_factor: float = 0.6

    # ── Network ─────────────────────────────────────────────────────────────
    network_ws_k_neighbors: int = 6
    network_ws_rewire_prob: float = 0.1
    network_ba_m_edges: int = 3
    network_cross_community_prob: float = 0.02
    network_same_community_trust: float = 0.7
    network_cross_community_trust: float = 0.3

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
