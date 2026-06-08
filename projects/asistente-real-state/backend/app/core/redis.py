import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


# Session memory helpers (WhatsApp conversation window)
SESSION_TTL = 86400  # 24h


async def get_session(wa_contact_id: str) -> list[dict]:
    r = await get_redis()
    import json
    raw = await r.get(f"session:{wa_contact_id}")
    return json.loads(raw) if raw else []


async def set_session(wa_contact_id: str, messages: list[dict]):
    r = await get_redis()
    import json
    await r.setex(f"session:{wa_contact_id}", SESSION_TTL, json.dumps(messages))


async def append_to_session(wa_contact_id: str, message: dict, max_k: int = 10):
    messages = await get_session(wa_contact_id)
    messages.append(message)
    await set_session(wa_contact_id, messages[-max_k:])


async def clear_session(wa_contact_id: str):
    r = await get_redis()
    await r.delete(f"session:{wa_contact_id}")
