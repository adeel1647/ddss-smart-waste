from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.schemas.routing import RoutingRequest, RoutingResponse, Trip, PlanLatestRequest, PlanLatestResponse
from app.services.routing import Point as SPoint, optimize_capacity_constrained
from app.repositories.decisions import latest_run, list_items_for_run
from app.repositories.bins import get_bin
from app.repositories.routes import create_plan, add_trip, trips_for_plan

router = APIRouter(tags=["routing"])

@router.post("/routing/optimize", response_model=RoutingResponse)
def optimize(req: RoutingRequest):
    points = [SPoint(id=p.id, lat=p.lat, lon=p.lon, priority=p.priority, demand=p.demand) for p in req.points]
    total_km, trips = optimize_capacity_constrained(
        depot_lat=req.depot_lat,
        depot_lon=req.depot_lon,
        points=points,
        capacity=req.capacity,
        strategy=req.strategy,
        epsilon=settings.epsilon,
    )
    return RoutingResponse(
        strategy=req.strategy,
        total_distance_km=float(total_km),
        trips=[Trip(stops=t["stops"], trip_distance_km=float(t["trip_distance_km"])) for t in trips],
    )

@router.post("/routing/plan-latest", response_model=PlanLatestResponse)
async def plan_latest(req: PlanLatestRequest, session: AsyncSession = Depends(get_session)):
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail="No decision run found (run /ddss/run first).")

    items = await list_items_for_run(session, run.id)
    items = items[: req.top_n]

    points: list[SPoint] = []
    for it in items:
        b = await get_bin(session, it.bin_id)
        if b is None:
            continue
        points.append(SPoint(
            id=it.bin_id,
            lat=float(b.lat),
            lon=float(b.lon),
            priority=float(it.priority_score),
            demand=float(it.predicted_fill_6h),
        ))

    if not points:
        raise HTTPException(status_code=400, detail="No routable points (bins must have locations and DDSS items).")

    total_km, trips = optimize_capacity_constrained(
        depot_lat=req.depot_lat,
        depot_lon=req.depot_lon,
        points=points,
        capacity=req.capacity,
        strategy=req.strategy,
        epsilon=settings.epsilon,
    )

    plan = await create_plan(
        session=session,
        decision_run_id=run.id,
        strategy=req.strategy,
        capacity=req.capacity,
        depot_lat=req.depot_lat,
        depot_lon=req.depot_lon,
        total_distance_km=float(total_km),
    )

    for idx, t in enumerate(trips):
        await add_trip(session, plan_id=plan.id, trip_index=idx, stops=t["stops"], trip_distance_km=float(t["trip_distance_km"]))

    stored = await trips_for_plan(session, plan.id)
    out_trips = [Trip(stops=json.loads(tr.stops_json), trip_distance_km=float(tr.trip_distance_km)) for tr in stored]

    return PlanLatestResponse(
        plan_id=plan.id,
        ts=plan.ts,
        decision_run_id=run.id,
        strategy=req.strategy,
        total_distance_km=float(total_km),
        trips=out_trips,
    )
