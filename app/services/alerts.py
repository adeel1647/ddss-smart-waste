from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, DecisionItem, DecisionRun


ALERT_MESSAGES = {
    "CRITICAL_FILL_PREDICTED": "Predicted fill exceeds critical threshold within 6 hours.",
    "OVERDUE_COLLECTION": "Bin has exceeded collection interval threshold.",
    "LOW_CLASSIFICATION_CONFIDENCE": "Latest image classification confidence is low.",
    "STALE_TELEMETRY": "Bin has not received recent telemetry.",
    "NO_RECENT_CLASSIFICATION": "No recent image classification found.",
    "ROUTE_CAPACITY_RISK": "Planned route may exceed vehicle capacity.",
}


def alert_severity(alert_type: str) -> str:
    if alert_type in {"CRITICAL_FILL_PREDICTED", "OVERDUE_COLLECTION", "ROUTE_CAPACITY_RISK"}:
        return "critical"
    if alert_type in {"LOW_CLASSIFICATION_CONFIDENCE", "STALE_TELEMETRY", "NO_RECENT_CLASSIFICATION"}:
        return "warning"
    return "info"


async def generate_alerts_for_run(session: AsyncSession, run_id: int) -> int:
    run = await session.get(DecisionRun, run_id)
    if not run:
        return 0

    result = await session.execute(
        select(DecisionItem).where(DecisionItem.run_id == run_id)
    )
    items = result.scalars().all()

    created = 0

    for item in items:
        try:
            alert_types = json.loads(item.alerts_json or "[]")
        except Exception:
            alert_types = []

        active_types = set(alert_types)

        existing_result = await session.execute(
            select(Alert).where(
                Alert.bin_id == item.bin_id,
                Alert.status.in_(["open", "acknowledged"]),
            )
        )
        existing_alerts = existing_result.scalars().all()
        existing_types = {a.alert_type for a in existing_alerts}

        # create missing open alerts
        for alert_type in active_types:
            if alert_type in existing_types:
                continue

            session.add(
                Alert(
                    bin_id=item.bin_id,
                    decision_run_id=run_id,
                    alert_type=alert_type,
                    severity=alert_severity(alert_type),
                    message=ALERT_MESSAGES.get(alert_type, alert_type.replace("_", " ").title()),
                    status="open",
                    meta_json=json.dumps(
                        {
                            "priority_score": item.priority_score,
                            "predicted_fill_6h": item.predicted_fill_6h,
                            "confidence": item.confidence,
                        }
                    ),
                )
            )
            created += 1

        # auto-resolve alerts that are no longer active
        for existing in existing_alerts:
            if existing.alert_type not in active_types and existing.status != "resolved":
                existing.status = "resolved"
                existing.resolved_at = datetime.now(timezone.utc)

    await session.commit()
    return created


async def list_alerts(
    session: AsyncSession,
    *,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)

    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_alert_summary(session: AsyncSession) -> dict:
    open_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open")
    ) or 0

    acknowledged_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "acknowledged")
    ) or 0

    resolved_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "resolved")
    ) or 0

    critical_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "critical")
    ) or 0

    warning_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "warning")
    ) or 0

    info_total = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "info")
    ) or 0

    return {
        "open_total": open_total,
        "critical_total": critical_total,
        "warning_total": warning_total,
        "info_total": info_total,
        "acknowledged_total": acknowledged_total,
        "resolved_total": resolved_total,
    }


async def update_alert_status(session: AsyncSession, alert_id: int, status: str) -> Alert | None:
    alert = await session.get(Alert, alert_id)
    if not alert:
        return None

    alert.status = status
    if status == "resolved":
        alert.resolved_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(alert)
    return alert