from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "asistente-real-state"}


@router.get("/health/detailed")
async def health_detailed(db: AsyncSession = Depends(get_db)):
    checks = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # pgvector
    try:
        await db.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        checks["pgvector"] = "ok"
    except Exception as e:
        checks["pgvector"] = f"error: {e}"

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            checks["ollama"] = {"status": "ok", "models": models}
    except Exception as e:
        checks["ollama"] = f"error: {e}"

    overall = "ok" if all(
        v == "ok" or (isinstance(v, dict) and v.get("status") == "ok")
        for v in checks.values()
    ) else "degraded"

    return {"status": overall, "checks": checks}
