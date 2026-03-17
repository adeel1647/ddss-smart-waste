from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.alerts import AlertListResponse, AlertOut, AlertSummaryOut, AlertUpdateIn
from app.services.alerts import list_alerts, get_alert_summary, update_alert_status

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    alerts = await list_alerts(session, status=status, severity=severity, limit=limit)
    return {
        "items": [
            AlertOut(
                id=a.id,
                bin_id=a.bin_id,
                decision_run_id=a.decision_run_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                status=a.status,
                meta=json.loads(a.meta_json or "{}"),
                created_at=a.created_at,
                resolved_at=a.resolved_at,
            )
            for a in alerts
        ]
    }


@router.get("/latest", response_model=AlertListResponse)
async def get_latest_alerts(
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    alerts = await list_alerts(session, limit=limit)
    return {
        "items": [
            AlertOut(
                id=a.id,
                bin_id=a.bin_id,
                decision_run_id=a.decision_run_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                status=a.status,
                meta=json.loads(a.meta_json or "{}"),
                created_at=a.created_at,
                resolved_at=a.resolved_at,
            )
            for a in alerts
        ]
    }


@router.get("/summary", response_model=AlertSummaryOut)
async def get_alerts_summary(
    session: AsyncSession = Depends(get_session),
):
    return await get_alert_summary(session)


@router.patch("/{alert_id}", response_model=AlertOut)
async def patch_alert(
    alert_id: int,
    payload: AlertUpdateIn,
    session: AsyncSession = Depends(get_session),
):
    if payload.status not in {"acknowledged", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid alert status")

    alert = await update_alert_status(session, alert_id, payload.status)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertOut(
        id=alert.id,
        bin_id=alert.bin_id,
        decision_run_id=alert.decision_run_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        status=alert.status,
        meta=json.loads(alert.meta_json or "{}"),
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )