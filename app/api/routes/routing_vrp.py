from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_session
from app.repositories.bins import get_bins_by_ids
from app.repositories.decisions import latest_run, list_items_for_run
from app.repositories.routes import create_plan_with_trips, trips_for_plan
from app.services.routing_vrp import VrpNode, solve_vrp

router = APIRouter(tags=['routing'])


class PlanLatestVrpRequest(BaseModel):
    depot_lat: float
    depot_lon: float
    capacity: int = Field(ge=1, description='Vehicle capacity in demand units')
    max_vehicles: int = Field(default=6, ge=1, le=20)
    top_n: int = Field(default=50, ge=1, le=500)
    priority_weight: float = Field(default=10.0, ge=0.0, le=500.0)
    use_osrm: bool = Field(default=True, description='Fetch road geometry via OSRM (may be rate-limited)')


@router.post('/routing/plan-latest-vrp')
async def plan_latest_vrp(
    req: PlanLatestVrpRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        f'route-vrp:{client_ip}',
        limit=settings.route_plan_rate_limit_per_minute,
        window_seconds=60,
        detail='Too many VRP planning requests. Please wait a moment and try again.',
    )

    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail='No decision run found (run /ddss/run first).')

    items = (await list_items_for_run(session, run.id))[: req.top_n]
    bins_by_id = await get_bins_by_ids(session, [it.bin_id for it in items])

    nodes: list[VrpNode] = [VrpNode(key='DEPOT', lat=req.depot_lat, lon=req.depot_lon, demand=0, priority=0.0)]
    total_demand = 0

    for it in items:
        b = bins_by_id.get(it.bin_id)
        if b is None:
            continue

        demand = int(round(max(0.0, min(100.0, float(it.predicted_fill_6h)))))
        total_demand += demand
        nodes.append(
            VrpNode(
                key=it.bin_id,
                lat=float(b.lat),
                lon=float(b.lon),
                demand=demand,
                priority=float(it.priority_score),
            )
        )

    if len(nodes) <= 1:
        raise HTTPException(status_code=400, detail='No routable points (bins must have locations and DDSS items).')

    vehicles = max(1, min(req.max_vehicles, (total_demand + req.capacity - 1) // req.capacity))

    result = await solve_vrp(
        nodes=nodes,
        vehicle_capacity=req.capacity,
        vehicles=vehicles,
        priority_weight=req.priority_weight,
        use_osrm_geometry=req.use_osrm,
    )

    plan, _ = await create_plan_with_trips(
        session,
        decision_run_id=run.id,
        strategy='vrp',
        capacity=float(req.capacity),
        depot_lat=req.depot_lat,
        depot_lon=req.depot_lon,
        total_distance_km=float(result['total_distance_km']),
        trips=result['trips'],
    )
    await session.commit()

    stored = await trips_for_plan(session, plan.id)
    geometry_by_index = {i + 1: result['trips'][i].get('geometry') for i in range(len(result['trips']))}

    out_trips = []
    for tr in stored:
        stops = json.loads(tr.stops_json or '[]')
        out_trips.append(
            {
                'stops': stops,
                'trip_distance_km': float(tr.trip_distance_km),
                'geometry': geometry_by_index.get(tr.trip_index),
            }
        )

    return {
        'plan_id': plan.id,
        'ts': plan.ts,
        'decision_run_id': run.id,
        'strategy': 'vrp',
        'total_distance_km': float(result['total_distance_km']),
        'trips': out_trips,
    }
