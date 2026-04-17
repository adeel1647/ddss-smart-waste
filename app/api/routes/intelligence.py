from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, get_current_user, require_org_permission
from app.db.models import User
from app.db.session import get_session
from app.repositories.intelligence import (
    create_contamination_case,
    create_model_metric_snapshot,
    get_contamination_case,
    list_contamination_cases,
    update_contamination_case,
)
from app.schemas.intelligence import (
    AnomalyEventOut,
    AnomalyListResponse,
    ContaminationCaseCreate,
    ContaminationCaseListResponse,
    ContaminationCaseOut,
    ContaminationCaseUpdate,
    ExplainabilityOut,
    ModelMetricSnapshotCreate,
    ModelMetricSnapshotOut,
    MonitoringSummaryOut,
    RiskListResponse,
    RiskScoreOut,
)
from app.services.audit import log_audit
from app.services.intelligence import build_anomaly_events, build_explainability, build_monitoring_summary, build_risk_scores

router = APIRouter(prefix='/intelligence', tags=['intelligence'])


@router.get('/risk/latest', response_model=RiskListResponse)
async def get_latest_risk_scores(
    request: Request,
    organisation_id: int | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'intelligence:read')
    forecaster = request.app.state.forecast_service
    items = await build_risk_scores(session, forecaster=forecaster, organisation_id=ctx.organisation_id, limit=limit)
    return {'items': [RiskScoreOut(**item) for item in items]}


@router.get('/anomalies', response_model=AnomalyListResponse)
async def get_anomalies(
    request: Request,
    organisation_id: int | None = Query(default=None),
    hours: int = Query(default=48, ge=6, le=336),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'intelligence:read')

    forecaster = request.app.state.forecast_service

    items = await build_anomaly_events(
        session,
        forecaster=forecaster,
        organisation_id=ctx.organisation_id,
        hours=hours,
        limit=limit,
    )
    return {'items': [AnomalyEventOut(**item) for item in items]}

@router.get('/explain/bin/{bin_id}', response_model=ExplainabilityOut)
async def get_bin_explainability(
    bin_id: str,
    request: Request,
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'intelligence:read')
    forecaster = request.app.state.forecast_service
    item = await build_explainability(session, forecaster=forecaster, bin_id=bin_id)
    if item is None:
        raise HTTPException(status_code=404, detail='Explainability record could not be generated for this bin')
    if ctx.organisation_id is not None and item.get('organisation_id') not in {None, ctx.organisation_id}:
        raise HTTPException(status_code=403, detail='Bin is outside the active organisation')
    return ExplainabilityOut(**item)


@router.get('/contamination/cases', response_model=ContaminationCaseListResponse)
async def get_contamination_cases(
    organisation_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'contamination:read')
    rows = await list_contamination_cases(session, organisation_id=ctx.organisation_id, status=status, limit=limit)
    return {'items': [_map_case(row) for row in rows]}


@router.post('/contamination/cases', response_model=ContaminationCaseOut)
async def post_contamination_case(
    payload: ContaminationCaseCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, payload.organisation_id)
    if ctx.organisation_id is None:
        raise HTTPException(status_code=400, detail='organisation_id is required')
    await require_org_permission(session, user, ctx.organisation_id, 'contamination:write')
    row = await create_contamination_case(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='contamination_case.create', entity_type='contamination_case', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_case(row)


@router.patch('/contamination/cases/{case_id}', response_model=ContaminationCaseOut)
async def patch_contamination_case(
    case_id: int,
    payload: ContaminationCaseUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = await get_contamination_case(session, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Contamination case not found')
    if row.organisation_id is not None:
        await require_org_permission(session, user, row.organisation_id, 'contamination:write')
    row = await update_contamination_case(session, row, **payload.model_dump(exclude_unset=True))
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='contamination_case.update', entity_type='contamination_case', entity_id=str(row.id), details=payload.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(row)
    return _map_case(row)


@router.post('/monitoring/snapshots', response_model=ModelMetricSnapshotOut)
async def post_model_metric_snapshot(
    payload: ModelMetricSnapshotCreate,
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'model_monitoring:write')
    elif not user.is_admin:
        raise HTTPException(status_code=403, detail='Only owners or platform admins can create monitoring snapshots')
    row = await create_model_metric_snapshot(session, **payload.model_dump())
    await log_audit(session, organisation_id=ctx.organisation_id, actor_user_id=user.id, action='model_metric_snapshot.create', entity_type='model_metric_snapshot', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_metric(row)


@router.get('/monitoring/summary', response_model=MonitoringSummaryOut)
async def get_model_monitoring_summary(
    request: Request,
    organisation_id: int | None = Query(default=None),
    model_name: str | None = Query(default=None),
    days: int = Query(default=14, ge=1, le=180),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'model_monitoring:read')

    forecaster = getattr(request.app.state, "forecast_service", None)

    return MonitoringSummaryOut(**(
        await build_monitoring_summary(
            session,
            model_name=model_name,
            days=days,
            organisation_id=ctx.organisation_id,
            forecaster=forecaster,
        )
    ))

def _map_case(row) -> ContaminationCaseOut:
    return ContaminationCaseOut(
        id=row.id,
        organisation_id=row.organisation_id,
        site_id=row.site_id,
        zone_id=row.zone_id,
        bin_id=row.bin_id,
        source=row.source,
        contamination_type=row.contamination_type,
        severity=row.severity,
        probability=float(row.probability) if row.probability is not None else None,
        status=row.status,
        notes=row.notes,
        evidence=json.loads(row.evidence_json or '{}'),
        created_at=row.created_at,
        updated_at=row.updated_at,
        resolved_at=row.resolved_at,
    )


def _map_metric(row) -> ModelMetricSnapshotOut:
    return ModelMetricSnapshotOut(
        id=row.id,
        model_name=row.model_name,
        model_version=row.model_version,
        metric_name=row.metric_name,
        metric_value=float(row.metric_value),
        window_label=row.window_label,
        sample_size=row.sample_size,
        status=row.status,
        meta=json.loads(row.meta_json or '{}'),
        created_at=row.created_at,
    )
