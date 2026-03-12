from __future__ import annotations

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging

from app.api.routes.health import router as health_router
from app.api.routes.bins import router as bins_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.classify import router as classify_router
from app.api.routes.forecast import router as forecast_router
from app.api.routes.ddss_run import router as ddss_run_router
from app.api.routes.ddss_latest import router as ddss_latest_router
from app.api.routes.routing import router as routing_router
from app.api.routes.routing_latest import router as routing_latest_router
from app.api.routes.routing_vrp import router as routing_vrp_router

from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router

from app.services.model_store import ModelStore
from app.services.classifier import ClassifierService
from app.services.forecaster import ForecastService

from app.db.init_db import init_db
from app.db.session import engine  # ✅ engine exists in your init_db.py, so use it here too


async def ensure_sequences() -> None:
    """
    Ensure DB sequences exist (useful if DB is dropped/recreated).
    Uses engine directly to avoid depending on session-maker naming.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS public.bin_seq START 1;"))


def create_app() -> FastAPI:
    setup_logging()
    log = logging.getLogger("app")
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health_router, prefix=prefix)
    app.include_router(bins_router, prefix=prefix)
    app.include_router(telemetry_router, prefix=prefix)
    app.include_router(classify_router, prefix=prefix)
    app.include_router(forecast_router, prefix=prefix)
    app.include_router(ddss_run_router, prefix=prefix)
    app.include_router(ddss_latest_router, prefix=prefix)
    app.include_router(routing_router, prefix=prefix)
    app.include_router(routing_latest_router, prefix=prefix)
    app.include_router(routing_vrp_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    

    @app.on_event("startup")
    async def _startup() -> None:
        # 1) Create tables
        await init_db()
        log.info("Database initialized (tables created).")

        # 2) Ensure sequences
        await ensure_sequences()
        log.info("Database sequences ensured (public.bin_seq).")

        # 3) Load models
        classifier_path = os.path.abspath(settings.classifier_model_path)
        forecast_path = os.path.abspath(settings.forecast_model_path)

        class_names = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]

        if os.path.exists(classifier_path):
            ModelStore.set_classifier(ClassifierService.load(classifier_path))
            app.state.classifier_service = ClassifierService(class_names=class_names)
            log.info("Loaded classifier model from %s", classifier_path)
        else:
            app.state.classifier_service = ClassifierService(class_names=class_names)
            log.warning("Classifier model not found at %s", classifier_path)

        if os.path.exists(forecast_path):
            ModelStore.set_forecaster(ForecastService.load(forecast_path))
            app.state.forecast_service = ForecastService()
            log.info("Loaded forecast model from %s", forecast_path)
        else:
            app.state.forecast_service = ForecastService()
            log.warning("Forecast model not found at %s", forecast_path)

    return app


app = create_app()