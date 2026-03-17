from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.routing_metrics import RoutingImpactOut
from app.services.route_metrics import get_latest_route_impact

router = APIRouter(prefix="/routing", tags=["routing-impact"])


@router.get("/impact/latest", response_model=RoutingImpactOut)
async def routing_impact_latest(
    session: AsyncSession = Depends(get_session),
):
    data = await get_latest_route_impact(session)
    if not data:
        raise HTTPException(status_code=404, detail="No route plan found")
    return data