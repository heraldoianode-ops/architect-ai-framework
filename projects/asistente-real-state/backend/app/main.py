import structlog
import sentry_sdk
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.core.redis import close_redis
from app.routers import health

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", environment=settings.environment, llm_mode="local" if not settings.allow_external_llm else "gated_external")
    yield
    await close_redis()
    await engine.dispose()
    log.info("shutdown")


# ─── Sentry (only in production) ────────────────────────────────────────────
if settings.sentry_dsn and settings.environment == "production":
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Asistente Real State API",
    version="0.1.0",
    description="PropTech AI — Ecosistema Operacional Autónomo",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router)

# TODO (next nodes):
# app.include_router(auth.router,       prefix="/auth")
# app.include_router(properties.router, prefix="/properties")
# app.include_router(clients.router,    prefix="/clients")
# app.include_router(events.router,     prefix="/events")
# app.include_router(agent.router,      prefix="/agent")
# app.include_router(analytics.router,  prefix="/analytics")
# app.include_router(admin.router,      prefix="/admin")
