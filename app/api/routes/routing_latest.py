from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.routes import latest_plan, trips_for_plan
from app.schemas.latest import LatestRouteResponse
from app.schemas.routing import Trip

router = APIRouter(tags=["routing"])

@router.get("/routing/latest", response_model=LatestRouteResponse)
async def latest_route(session: AsyncSession = Depends(get_session)):
    plan = await latest_plan(session)
    if plan is None:
        raise HTTPException(status_code=404, detail="No route plan found.")
    trips = await trips_for_plan(session, plan.id)
    out_trips = [Trip(stops=json.loads(t.stops_json), trip_distance_km=float(t.trip_distance_km)) for t in trips]
    return LatestRouteResponse(
        plan_id=plan.id,
        ts=plan.ts,
        decision_run_id=int(plan.decision_run_id),
        strategy=plan.strategy,
        total_distance_km=float(plan.total_distance_km),
        trips=out_trips,
    )
