from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Bin, DecisionItem, DecisionRun


ALERT_MESSAGES = {
    'CRITICAL_FILL_PREDICTED': 'Predicted fill exceeds the critical threshold within 6 hours.',
    'COLLECTION_DUE_SOON': 'Bin is approaching its scheduled collection window.',
    'OVERDUE_COLLECTION': 'Bin has exceeded its scheduled collection interval.',
    'LOW_CLASSIFICATION_CONFIDENCE': 'Latest image classification confidence is low.',
    'STALE_TELEMETRY': 'Bin has not received recent telemetry.',
    'NO_RECENT_CLASSIFICATION': 'No recent image classification found.',
    'ROUTE_CAPACITY_RISK': 'Planned route may exceed vehicle capacity.',
}


def alert_severity(alert_type: str) -> str:
    if alert_type in {'CRITICAL_FILL_PREDICTED', 'OVERDUE_COLLECTION', 'ROUTE_CAPACITY_RISK'}:
        return 'critical'
    if alert_type in {'COLLECTION_DUE_SOON', 'LOW_CLASSIFICATION_CONFIDENCE', 'STALE_TELEMETRY', 'NO_RECENT_CLASSIFICATION'}:
        return 'warning'
    return 'info'


async def generate_alerts_for_run(session: AsyncSession, run_id: int, *, commit: bool = True) -> int:
    run = await session.get(DecisionRun, run_id)
    if not run:
        return 0

    result = await session.execute(select(DecisionItem).where(DecisionItem.run_id == run_id))
    items = result.scalars().all()
    if not items:
        return 0

    bin_ids = [item.bin_id for item in items]
    existing_result = await session.execute(
        select(Alert).where(
            Alert.bin_id.in_(bin_ids),
            Alert.status.in_(['open', 'acknowledged']),
        )
    )
    existing_by_bin: dict[str, list[Alert]] = {}
    for alert in existing_result.scalars().all():
        existing_by_bin.setdefault(alert.bin_id, []).append(alert)

    created = 0

    for item in items:
        try:
            active_types = set(json.loads(item.alerts_json or '[]'))
        except Exception:
            active_types = set()

        existing_alerts = existing_by_bin.get(item.bin_id, [])
        existing_types = {a.alert_type for a in existing_alerts}

        for alert_type in active_types:
            if alert_type in existing_types:
                continue
            session.add(
                Alert(
                    bin_id=item.bin_id,
                    decision_run_id=run_id,
                    alert_type=alert_type,
                    severity=alert_severity(alert_type),
                    message=ALERT_MESSAGES.get(alert_type, alert_type.replace('_', ' ').title()),
                    status='open',
                    meta_json=json.dumps(
                        {
                            'priority_score': item.priority_score,
                            'predicted_fill_6h': item.predicted_fill_6h,
                            'confidence': item.confidence,
                        }
                    ),
                )
            )
            created += 1

        for existing in existing_alerts:
            if existing.alert_type not in active_types and existing.status != 'resolved':
                existing.status = 'resolved'
                existing.resolved_at = datetime.now(timezone.utc)

    if commit:
        await session.commit()
    return created


async def list_alerts(
    session: AsyncSession,
    *,
    organisation_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[Alert]:
    stmt = select(Alert).join(Bin, Bin.bin_id == Alert.bin_id)
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_alert_summary(session: AsyncSession, organisation_id: int | None = None) -> dict:
    def _base():
        stmt = select(func.count()).select_from(Alert)
        if organisation_id is not None:
            stmt = stmt.join(Bin, Bin.bin_id == Alert.bin_id).where(Bin.organisation_id == organisation_id)
        return stmt

    open_total = await session.scalar(_base().where(Alert.status == 'open')) or 0
    acknowledged_total = await session.scalar(_base().where(Alert.status == 'acknowledged')) or 0
    resolved_total = await session.scalar(_base().where(Alert.status == 'resolved')) or 0
    critical_total = await session.scalar(_base().where(Alert.status == 'open', Alert.severity == 'critical')) or 0
    warning_total = await session.scalar(_base().where(Alert.status == 'open', Alert.severity == 'warning')) or 0
    info_total = await session.scalar(_base().where(Alert.status == 'open', Alert.severity == 'info')) or 0

    return {
        'open_total': open_total,
        'critical_total': critical_total,
        'warning_total': warning_total,
        'info_total': info_total,
        'acknowledged_total': acknowledged_total,
        'resolved_total': resolved_total,
    }


async def update_alert_status(session: AsyncSession, alert_id: int, status: str) -> Alert | None:
    alert = await session.get(Alert, alert_id)
    if not alert:
        return None

    alert.status = status
    if status == 'resolved':
        alert.resolved_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(alert)
    return alert
