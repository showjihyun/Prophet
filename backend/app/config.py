"""Application configuration.
SPEC: docs/spec/00_ARCHITECTURE.md#environment-variables
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://prophet:secret@localhost:5432/prophet"
    valkey_url: str = "valkey://localhost:6379/0"

    # LLM Providers
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    slm_model: str = "phi4"
    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o"

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Simulation Defaults
    default_llm_provider: str = "ollama"
    llm_tier3_ratio: float = 0.1
    llm_cache_ttl: int = 3600

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
