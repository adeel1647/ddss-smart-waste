from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.model_store import ModelStore

router = APIRouter(tags=['health'])


@router.get('/health')
def health(request: Request):
    return {
        'status': 'ok',
        'app': request.app.title,
    }


@router.get('/health/models')
def health_models():
    model_health = ModelStore.get_health()
    overall = 'ok' if model_health['classifier']['loaded'] and model_health['forecaster']['loaded'] else 'degraded'
    return {
        'status': overall,
        'models': model_health,
    }
