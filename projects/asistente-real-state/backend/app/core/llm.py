"""
LLM factory — enforces ai_policy.
Default: Ollama local (zero token cost).
External: only when allow_external=True AND agent is authorized.
"""
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from app.core.config import get_settings

settings = get_settings()


def get_llm(agent_name: str | None = None):
    """Return the correct LLM. Never uses external API without explicit authorization."""
    mode, model = settings.get_llm(agent_name)

    if mode == "external":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=0.2,
        )

    return OllamaLLM(
        model=model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
        timeout=settings.ollama_timeout,
    )


def get_embeddings():
    """Always use local embeddings (nomic-embed-text via Ollama). Zero cost."""
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )
