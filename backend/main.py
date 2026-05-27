from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.agent_runtime import build_agent_runtime
from core.logging import configure_logging
from orchestrator.pipeline import hydrate_caches
from routers import auth_router, health_router, rfp_router
from services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    app.state.server_boot_id = uuid.uuid4().hex
    app.state.agent_runtime = await build_agent_runtime(settings)
    start_scheduler()
    # Restore persisted run history so the API exposes it immediately after restart.
    try:
        restored = hydrate_caches()
        if restored:
            app.state.restored_runs = restored
    except Exception:  # noqa: BLE001
        pass
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="Microsoft Agent Framework — RFP Intelligence Pipeline",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(rfp_router, prefix="/api/v1/rfp", tags=["RFP"])
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    return app


app = create_app()
