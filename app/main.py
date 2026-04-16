from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.api.routes.alerts import router as alerts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bins import router as bins_router
from app.api.routes.classify import router as classify_router
from app.api.routes.ddss_latest import router as ddss_latest_router
from app.api.routes.ddss_run import router as ddss_run_router
from app.api.routes.forecast import router as forecast_router
from app.api.routes.geo import router as geo_router
from app.api.routes.health import router as health_router
from app.api.routes.map import router as map_router
from app.api.routes.ops import router as ops_router
from app.api.routes.public import router as public_router
from app.api.routes.routing import router as routing_router
from app.api.routes.routing_latest import router as routing_latest_router
from app.api.routes.routing_metrics import router as routing_metrics_router
from app.api.routes.routing_vrp import router as routing_vrp_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.users import router as users_router
from app.api.routes.work_orders import router as work_orders_router
from app.api.routes.enterprise import router as enterprise_router
from app.api.routes.intelligence import router as intelligence_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import engine
from app.services.classifier import ClassifierService
from app.services.forecaster import ForecastService
from app.services.model_store import ModelStore


async def ensure_sequences() -> None:
    async with engine.begin() as conn:
        await conn.execute(text('CREATE SEQUENCE IF NOT EXISTS public.bin_seq START 1;'))


def create_app() -> FastAPI:
    setup_logging()
    log = logging.getLogger('app')
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
        expose_headers=['X-Request-ID'],
    )

    @app.middleware('http')
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
        start = time.perf_counter()
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except SQLAlchemyError as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception(
                'Database request error',
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': duration_ms,
                    'client_ip': request.client.host if request.client else 'unknown',
                },
            )

            db_message = str(getattr(exc, "orig", exc)) or exc.__class__.__name__

            return JSONResponse(
                status_code=500,
                content={
                    'detail': db_message,
                    'error_type': exc.__class__.__name__,
                    'request_id': request_id,
                },
                headers={'X-Request-ID': request_id},
            )

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception(
                'Unhandled request error',
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': duration_ms,
                    'client_ip': request.client.host if request.client else 'unknown',
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    'detail': str(exc) or 'Internal server error',
                    'error_type': exc.__class__.__name__,
                    'request_id': request_id,
                },
                headers={'X-Request-ID': request_id},
            )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            'Request completed',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'client_ip': request.client.host if request.client else 'unknown',
            },
        )
        response.headers['X-Request-ID'] = request_id
        return response

    prefix = settings.api_prefix
    if not prefix.startswith('/'):
        raise ValueError(f"API_PREFIX must start with '/'. Current value: {prefix!r}")

    app.include_router(health_router, prefix=prefix)
    app.include_router(geo_router, prefix=prefix)
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
    app.include_router(alerts_router, prefix=prefix)
    app.include_router(ops_router, prefix=prefix)
    app.include_router(map_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(routing_metrics_router, prefix=prefix)
    app.include_router(work_orders_router, prefix=prefix)
    app.include_router(enterprise_router, prefix=prefix)
    app.include_router(intelligence_router, prefix=prefix)
    app.include_router(public_router, prefix=prefix)

    @app.on_event('startup')
    async def _startup() -> None:
        await init_db()
        log.info('Database connection verified.')

        await ensure_sequences()
        log.info('Database sequences ensured (public.bin_seq).')

        classifier_path = os.path.abspath(settings.classifier_model_path)
        forecast_path = os.path.abspath(settings.forecast_model_path)

        class_names = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']

        app.state.classifier_service = ClassifierService(class_names=class_names)
        app.state.forecast_service = ForecastService()

        if os.path.exists(classifier_path):
            model = ClassifierService.load(classifier_path)
            ModelStore.set_classifier(model, path=classifier_path)
            log.info('Loaded classifier model from %s', classifier_path)
        else:
            ModelStore.set_classifier(None, path=classifier_path)
            log.warning('Classifier model not found at %s', classifier_path)

        if os.path.exists(forecast_path):
            model = ForecastService.load(forecast_path)
            ModelStore.set_forecaster(model, path=forecast_path)
            log.info('Loaded forecast model from %s', forecast_path)
        else:
            ModelStore.set_forecaster(None, path=forecast_path)
            log.warning('Forecast model not found at %s', forecast_path)

    return app


app = create_app()
