from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, get_current_user, require_org_permission
from app.db.models import Alert, User
from app.db.session import get_session
from app.repositories.decisions import latest_run, list_items_for_run
from app.repositories.routes import latest_plan
from app.repositories.work_orders import (
    create_work_orders_from_alerts,
    create_work_orders_from_latest_route,
    get_work_order,
    get_work_order_organisation_id,
    list_work_orders,
    update_work_order,
)
from app.schemas.work_orders import (
    WorkOrderCreateFromAlerts,
    WorkOrderCreateFromLatestRoute,
    WorkOrderOut,
    WorkOrderUpdateIn,
)

router = APIRouter(prefix='/work-orders', tags=['work-orders'])


@router.get('', response_model=list[WorkOrderOut])
async def get_work_orders(
    organisation_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'work_order:read')
    assigned_to = None
    if ctx.role == 'operator':
        assigned_to = user.email
    rows = await list_work_orders(session, organisation_id=ctx.organisation_id, status=status, priority=priority, assigned_to=assigned_to, limit=limit)
    # fallback to display_name matching for operators if email-based assignment not used
    if ctx.role == 'operator' and not rows and user.display_name:
        rows = await list_work_orders(session, organisation_id=ctx.organisation_id, status=status, priority=priority, assigned_to=user.display_name, limit=limit)
    return [_map_work_order(row) for row in rows]


@router.post('/from-alerts', response_model=list[WorkOrderOut])
async def create_from_alerts(
    payload: WorkOrderCreateFromAlerts,
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is None:
        raise HTTPException(status_code=400, detail='organisation_id is required for this action')
    await require_org_permission(session, user, ctx.organisation_id, 'work_order:write')

    alert_ids = payload.alert_ids
    if not alert_ids:
        result = await session.execute(
            select(Alert.id)
            .where(Alert.status == 'open')
            .order_by(Alert.created_at.desc())
            .limit(25)
        )
        alert_ids = [row[0] for row in result.all()]
    rows = await create_work_orders_from_alerts(
        session,
        alert_ids=alert_ids,
        assigned_to=payload.assigned_to,
        due_hours=payload.due_hours,
        organisation_id=ctx.organisation_id,
    )
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return [_map_work_order(row) for row in rows]


@router.post('/from-latest-route', response_model=list[WorkOrderOut])
async def create_from_latest_route(
    payload: WorkOrderCreateFromLatestRoute,
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is None:
        raise HTTPException(status_code=400, detail='organisation_id is required for this action')
    await require_org_permission(session, user, ctx.organisation_id, 'work_order:write')
    plan = await latest_plan(session)
    if plan is None:
        raise HTTPException(status_code=404, detail='No route plan found.')
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail='No decision run found.')
    items = await list_items_for_run(session, run.id)
    selected_bin_ids = [item.bin_id for item in sorted(items, key=lambda x: x.priority_score, reverse=True)[: payload.top_n]]
    rows = await create_work_orders_from_latest_route(
        session,
        plan_id=plan.id,
        bin_ids=selected_bin_ids,
        assigned_to=payload.assigned_to,
        due_hours=payload.due_hours,
        organisation_id=ctx.organisation_id,
    )
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return [_map_work_order(row) for row in rows]


@router.patch('/{work_order_id}', response_model=WorkOrderOut)
async def patch_work_order(
    work_order_id: int,
    payload: WorkOrderUpdateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = await get_work_order(session, work_order_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Work order not found')
    organisation_id = await get_work_order_organisation_id(session, work_order_id)
    if organisation_id is None:
        raise HTTPException(status_code=404, detail='Related organisation not found')
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.role == 'operator':
        allowed_assignees = {value for value in [user.email, user.display_name] if value}
        if row.assigned_to not in allowed_assignees:
            raise HTTPException(status_code=403, detail='Operators can update only work orders assigned to them')
        if payload.assigned_to is not None and payload.assigned_to != row.assigned_to:
            raise HTTPException(status_code=403, detail='Operators cannot reassign work orders')
        if payload.status is not None and payload.status not in {'in_progress', 'resolved', 'completed', 'closed'}:
            raise HTTPException(status_code=403, detail='Operators can only progress or complete assigned work orders')
    else:
        await require_org_permission(session, user, organisation_id, 'work_order:write')
    row = await update_work_order(
        session,
        work_order_id,
        status=payload.status,
        assigned_to=payload.assigned_to,
        resolution_notes=payload.resolution_notes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail='Work order not found')
    return _map_work_order(row)


def _map_work_order(row) -> WorkOrderOut:
    return WorkOrderOut(
        id=row.id,
        bin_id=row.bin_id,
        alert_id=row.alert_id,
        route_plan_id=row.route_plan_id,
        title=row.title,
        description=row.description,
        priority=row.priority,
        status=row.status,
        assigned_to=row.assigned_to,
        due_at=row.due_at,
        resolution_notes=row.resolution_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )
