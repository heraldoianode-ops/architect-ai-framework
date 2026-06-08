from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    # Supabase (optional, for Auth + Storage)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # ─── AI Policy (local-first) ────────────────────────────────
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 120

    # External LLM — only used when allow_external=true
    allow_external_llm: bool = False
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    external_llm_model: str = "claude-sonnet-4-6"

    # Agents authorized for external LLM
    external_llm_authorized_agents: list[str] = [
        "rag_legal_agent",
        "objection_handler_agent",
        "predictive_report_agent",
    ]

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_verify_token: str = ""
    whatsapp_app_secret: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email
    resend_api_key: str = ""

    # Monitoring
    sentry_dsn: str = ""

    def get_llm(self, agent_name: str | None = None):
        """
        Returns the correct LLM based on ai_policy.
        External LLM only if allow_external=True AND agent is authorized.
        """
        if (
            self.allow_external_llm
            and agent_name
            and agent_name in self.external_llm_authorized_agents
            and self.anthropic_api_key
        ):
            return "external", self.external_llm_model
        return "local", self.ollama_llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
