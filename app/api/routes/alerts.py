from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, get_current_user, require_org_permission
from app.db.models import Alert, Bin, User
from app.db.session import get_session
from app.schemas.alerts import AlertListResponse, AlertOut, AlertSummaryOut, AlertUpdateIn
from app.services.alerts import get_alert_summary, list_alerts, update_alert_status

router = APIRouter(prefix='/alerts', tags=['alerts'])


@router.get('', response_model=AlertListResponse)
async def get_alerts(
    organisation_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'alert:read')
    alerts = await list_alerts(session, organisation_id=ctx.organisation_id, status=status, severity=severity, limit=limit)
    return {'items': [_map_alert(item) for item in alerts]}


@router.get('/latest', response_model=AlertListResponse)
async def get_latest_alerts(
    organisation_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'alert:read')
    alerts = await list_alerts(session, organisation_id=ctx.organisation_id, limit=limit)
    return {'items': [_map_alert(item) for item in alerts]}


@router.get('/summary', response_model=AlertSummaryOut)
async def get_alerts_summary(
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'alert:read')
    return await get_alert_summary(session, organisation_id=ctx.organisation_id)


@router.patch('/{alert_id}', response_model=AlertOut)
async def patch_alert(
    alert_id: int,
    payload: AlertUpdateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.status not in {'acknowledged', 'resolved'}:
        raise HTTPException(status_code=400, detail='Invalid alert status')

    result = await session.execute(select(Bin.organisation_id).select_from(Alert).join(Bin, Bin.bin_id == Alert.bin_id).where(Alert.id == alert_id))
    organisation_id = result.scalar_one_or_none()
    if organisation_id is None:
        raise HTTPException(status_code=404, detail='Alert not found')
    await require_org_permission(session, user, organisation_id, 'alert:write')

    alert = await update_alert_status(session, alert_id, payload.status)
    if not alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    return _map_alert(alert)


def _map_alert(alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        bin_id=alert.bin_id,
        decision_run_id=alert.decision_run_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        status=alert.status,
        meta=json.loads(alert.meta_json or '{}'),
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )
