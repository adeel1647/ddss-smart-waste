from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Bin, RoutePlan, WorkOrder


def _priority_from_severity(severity: str) -> str:
    if severity == 'critical':
        return 'high'
    if severity == 'warning':
        return 'medium'
    return 'low'


async def list_work_orders(
    session: AsyncSession,
    *,
    organisation_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    limit: int = 100,
) -> list[WorkOrder]:
    stmt = select(WorkOrder).join(Bin, Bin.bin_id == WorkOrder.bin_id)
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if priority:
        stmt = stmt.where(WorkOrder.priority == priority)
    if assigned_to:
        stmt = stmt.where(WorkOrder.assigned_to == assigned_to)
    stmt = stmt.order_by(WorkOrder.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_work_order(session: AsyncSession, work_order_id: int) -> WorkOrder | None:
    return await session.get(WorkOrder, work_order_id)


async def get_work_order_organisation_id(session: AsyncSession, work_order_id: int) -> int | None:
    result = await session.execute(
        select(Bin.organisation_id)
        .select_from(WorkOrder)
        .join(Bin, Bin.bin_id == WorkOrder.bin_id)
        .where(WorkOrder.id == work_order_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_work_orders_from_alerts(
    session: AsyncSession,
    *,
    alert_ids: list[int],
    assigned_to: str | None,
    due_hours: int,
    organisation_id: int | None = None,
) -> list[WorkOrder]:
    if not alert_ids:
        return []

    stmt = select(Alert).where(Alert.id.in_(alert_ids)).join(Bin, Bin.bin_id == Alert.bin_id)
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    result = await session.execute(stmt)
    alerts = list(result.scalars().all())
    existing_result = await session.execute(select(WorkOrder).where(WorkOrder.alert_id.in_(alert_ids), WorkOrder.status != 'completed'))
    existing_alert_ids = {item.alert_id for item in existing_result.scalars().all() if item.alert_id is not None}

    due_at = datetime.now(timezone.utc) + timedelta(hours=due_hours)
    rows: list[WorkOrder] = []
    for alert in alerts:
        if alert.id in existing_alert_ids:
            continue
        row = WorkOrder(
            bin_id=alert.bin_id,
            alert_id=alert.id,
            title=f'Inspect bin {alert.bin_id}',
            description=alert.message,
            priority=_priority_from_severity(alert.severity),
            status='open',
            assigned_to=assigned_to,
            due_at=due_at,
        )
        session.add(row)
        rows.append(row)

    if rows:
        await session.flush()
    return rows


async def create_work_orders_from_latest_route(
    session: AsyncSession,
    *,
    plan_id: int,
    bin_ids: list[str],
    assigned_to: str | None,
    due_hours: int,
    organisation_id: int | None = None,
) -> list[WorkOrder]:
    if not bin_ids:
        return []
    if organisation_id is not None:
        result = await session.execute(select(Bin.bin_id).where(Bin.bin_id.in_(bin_ids), Bin.organisation_id == organisation_id))
        allowed_bin_ids = {row[0] for row in result.all()}
        bin_ids = [bin_id for bin_id in bin_ids if bin_id in allowed_bin_ids]
    due_at = datetime.now(timezone.utc) + timedelta(hours=due_hours)
    rows: list[WorkOrder] = []
    for bin_id in bin_ids:
        row = WorkOrder(
            bin_id=bin_id,
            route_plan_id=plan_id,
            title=f'Collect bin {bin_id}',
            description='Collection task created from latest route plan.',
            priority='medium',
            status='open',
            assigned_to=assigned_to,
            due_at=due_at,
        )
        session.add(row)
        rows.append(row)
    if rows:
        await session.flush()
    return rows


async def update_work_order(
    session: AsyncSession,
    work_order_id: int,
    *,
    status: str | None = None,
    assigned_to: str | None = None,
    resolution_notes: str | None = None,
) -> WorkOrder | None:
    row = await session.get(WorkOrder, work_order_id)
    if not row:
        return None
    if status is not None:
        row.status = status
        if status in {'completed', 'resolved', 'closed'}:
            row.completed_at = datetime.now(timezone.utc)
    if assigned_to is not None:
        row.assigned_to = assigned_to or None
    if resolution_notes is not None:
        row.resolution_notes = resolution_notes or None
    await session.commit()
    await session.refresh(row)
    return row
