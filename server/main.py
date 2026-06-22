from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from graph import setup_graph, teardown_graph
from logging_config import configure_logging
from routers import health, me, session, user
from tracing import setup_tracing

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_tracing(settings)
    try:
        await setup_graph()
        logger.info("graph.ready")
    except Exception as exc:  # noqa: BLE001 — boot in degraded mode if DB is down
        logger.error("graph.setup_failed", error=str(exc))
    yield
    await teardown_graph()


app = FastAPI(title="depthed API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(user.router, prefix="/user", tags=["user"])
