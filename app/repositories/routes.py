from __future__ import annotations

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import RoutePlan, RouteTrip

async def create_plan(
    session: AsyncSession,
    decision_run_id: int,
    strategy: str,
    capacity: float,
    depot_lat: float,
    depot_lon: float,
    total_distance_km: float,
) -> RoutePlan:
    plan = RoutePlan(
        decision_run_id=decision_run_id,
        strategy=strategy,
        capacity=capacity,
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        total_distance_km=total_distance_km,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan

async def add_trip(session: AsyncSession, plan_id: int, trip_index: int, stops: list[str], trip_distance_km: float) -> RouteTrip:
    trip = RouteTrip(plan_id=plan_id, trip_index=trip_index, stops_json=json.dumps(stops), trip_distance_km=trip_distance_km)
    session.add(trip)
    await session.commit()
    await session.refresh(trip)
    return trip

async def latest_plan(session: AsyncSession) -> RoutePlan | None:
    res = await session.execute(select(RoutePlan).order_by(desc(RoutePlan.ts)).limit(1))
    return res.scalar_one_or_none()

async def trips_for_plan(session: AsyncSession, plan_id: int) -> list[RouteTrip]:
    res = await session.execute(select(RouteTrip).where(RouteTrip.plan_id == plan_id).order_by(RouteTrip.trip_index))
    return list(res.scalars().all())


async def latest_plan_with_trips(session: AsyncSession):
    plan = await latest_plan(session)
    if plan is None:
        return None, []
    trips = await trips_for_plan(session, plan.id)
    return plan, trips
