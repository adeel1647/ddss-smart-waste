from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.analytics import (
    AnalyticsOverviewOut,
    FillTrendResponse,
    TrendPoint,
    ClassDistributionResponse,
    ClassDistributionItem,
)
from app.services.analytics import get_analytics_overview, get_fill_trend, get_class_distribution

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewOut)
async def analytics_overview(
    session: AsyncSession = Depends(get_session),
):
    return await get_analytics_overview(session)


@router.get("/fill-trend", response_model=FillTrendResponse)
async def analytics_fill_trend(
    hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    points = await get_fill_trend(session, hours=hours)
    return {"points": [TrendPoint(**p) for p in points]}


@router.get("/class-distribution", response_model=ClassDistributionResponse)
async def analytics_class_distribution(
    hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
):
    items = await get_class_distribution(session, hours=hours)
    return {"items": [ClassDistributionItem(**i) for i in items]}