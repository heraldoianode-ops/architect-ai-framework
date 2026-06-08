"""
embedder.py — Generate text embeddings via Ollama nomic-embed-text.
Returns vector(768) as Python list[float].
Batch mode supported to avoid serial latency on large ingestion jobs.
"""
import asyncio
import httpx
import structlog
from typing import Sequence

from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()

EMBED_MODEL = settings.ollama_embed_model   # "nomic-embed-text"
OLLAMA_URL = settings.ollama_base_url       # "http://ollama:11434"
BATCH_SIZE = 16                             # parallel requests per batch
TIMEOUT = 30.0


async def _embed_one(client: httpx.AsyncClient, text: str) -> list[float]:
    """Call Ollama /api/embeddings for a single text."""
    resp = await client.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


async def embed_text(text: str) -> list[float]:
    """Embed a single string. Convenience wrapper."""
    async with httpx.AsyncClient() as client:
        return await _embed_one(client, text)


async def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    """
    Embed a list of strings in concurrent batches.
    Returns embeddings in the same order as input.
    """
    results: list[list[float] | None] = [None] * len(texts)

    async with httpx.AsyncClient() as client:
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch = texts[batch_start: batch_start + BATCH_SIZE]
            embeddings = await asyncio.gather(
                *[_embed_one(client, t) for t in batch],
                return_exceptions=True,
            )
            for i, emb in enumerate(embeddings):
                if isinstance(emb, Exception):
                    log.error("embedder.batch_error", idx=batch_start + i, error=str(emb))
                    results[batch_start + i] = [0.0] * 768  # zero vector on failure
                else:
                    results[batch_start + i] = emb

    return results  # type: ignore[return-value]
