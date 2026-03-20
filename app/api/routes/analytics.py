from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, get_current_user, require_org_permission
from app.db.models import User
from app.db.session import get_session
from app.schemas.analytics import (
    AnalyticsOverviewOut,
    FillTrendResponse,
    TrendPoint,
    ClassDistributionResponse,
    ClassDistributionItem,
)
from app.services.analytics import get_analytics_overview, get_fill_trend, get_class_distribution

router = APIRouter(prefix='/analytics', tags=['analytics'])


@router.get('/overview', response_model=AnalyticsOverviewOut)
async def analytics_overview(
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'analytics:read')
    return await get_analytics_overview(session, organisation_id=ctx.organisation_id)


@router.get('/fill-trend', response_model=FillTrendResponse)
async def analytics_fill_trend(
    organisation_id: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'analytics:read')
    points = await get_fill_trend(session, hours=hours, organisation_id=ctx.organisation_id)
    return {'points': [TrendPoint(**p) for p in points]}


@router.get('/class-distribution', response_model=ClassDistributionResponse)
async def analytics_class_distribution(
    organisation_id: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'analytics:read')
    items = await get_class_distribution(session, hours=hours, organisation_id=ctx.organisation_id)
    return {'items': [ClassDistributionItem(**i) for i in items]}
