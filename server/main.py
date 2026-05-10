from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from logging_config import configure_logging
from routers import health, me, session, user

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="depthed API", version="0.1.0")

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
