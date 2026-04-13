from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_session
from app.repositories.bins import get_bins_by_ids
from app.repositories.decisions import latest_run, list_items_for_run
from app.repositories.routes import create_plan_with_trips
from app.schemas.routing import PlanLatestRequest, PlanLatestResponse, RoutingRequest, RoutingResponse, Trip
from app.services.geocoding import GeocodingError, GeocodingService
from app.services.routing import Point as SPoint, optimize_capacity_constrained

router = APIRouter(tags=['routing'])


async def _resolve_depot(req: RoutingRequest | PlanLatestRequest):
    try:
        resolved = await GeocodingService.resolve(
            place_id=req.depot_place_id,
            query=req.depot_address,
            postcode=req.depot_postcode,
            address_line_1=req.depot_address_line_1,
            address_line_2=req.depot_address_line_2,
            city=req.depot_city,
            county=req.depot_county,
            country=req.depot_country,
            lat=req.depot_lat,
            lon=req.depot_lon,
            allow_manual_override=True,
        )
    except GeocodingError as exc:
        raise HTTPException(status_code=400, detail=f'Invalid depot location: {exc}') from exc
    return resolved


@router.post('/routing/optimize', response_model=RoutingResponse)
async def optimize(req: RoutingRequest, request: Request, _user=Depends(get_current_user)):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        f'route-optimize:{client_ip}',
        limit=settings.route_plan_rate_limit_per_minute,
        window_seconds=60,
        detail='Too many routing requests. Please wait a moment and try again.',
    )

    depot = await _resolve_depot(req)
    points = [SPoint(id=p.id, lat=p.lat, lon=p.lon, priority=p.priority, demand=p.demand) for p in req.points]
    total_km, trips = optimize_capacity_constrained(
        depot_lat=depot.lat,
        depot_lon=depot.lon,
        capacity=req.capacity,
        points=points,
        strategy=req.strategy,
    )
    return RoutingResponse(
        strategy=req.strategy,
        total_distance_km=round(total_km, 3),
        trips=[Trip(stops=t['stops'], trip_distance_km=round(t['trip_distance_km'], 3)) for t in trips],
        depot_display_name=depot.display_name,
        depot_lat=depot.lat,
        depot_lon=depot.lon,
    )


@router.post('/routing/plan-latest', response_model=PlanLatestResponse)
async def plan_latest(
    req: PlanLatestRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        f'route-plan:{client_ip}',
        limit=settings.route_plan_rate_limit_per_minute,
        window_seconds=60,
        detail='Too many route planning requests. Please wait a moment and try again.',
    )

    depot = await _resolve_depot(req)
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail='No decision run found (run /ddss/run first).')

    items = await list_items_for_run(session, run.id)
    if not items:
        raise HTTPException(status_code=404, detail='No decision items available for latest run.')

    selected = sorted(items, key=lambda x: x.priority_score, reverse=True)[: req.top_n]
    bins_by_id = await get_bins_by_ids(session, [item.bin_id for item in selected])

    points: list[SPoint] = []
    for item in selected:
        b = bins_by_id.get(item.bin_id)
        if not b:
            continue
        points.append(
            SPoint(
                id=item.bin_id,
                lat=float(b.lat),
                lon=float(b.lon),
                priority=float(item.priority_score),
                demand=float(min(max(item.predicted_fill_6h, 0.0), 100.0)),
            )
        )

    if not points:
        raise HTTPException(status_code=400, detail='Could not map decision items to bins for routing.')

    total_km, trips = optimize_capacity_constrained(
        depot_lat=depot.lat,
        depot_lon=depot.lon,
        capacity=req.capacity,
        points=points,
        strategy=req.strategy,
    )

    plan, trip_rows = await create_plan_with_trips(
        session,
        decision_run_id=run.id,
        strategy=req.strategy,
        capacity=req.capacity,
        depot_lat=depot.lat,
        depot_lon=depot.lon,
        total_distance_km=float(total_km),
        trips=trips,
    )
    await session.commit()

    return PlanLatestResponse(
        plan_id=plan.id,
        ts=plan.ts,
        decision_run_id=plan.decision_run_id,
        strategy=plan.strategy,
        total_distance_km=float(plan.total_distance_km),
        trips=[Trip(stops=json.loads(t.stops_json or '[]'), trip_distance_km=float(t.trip_distance_km)) for t in trip_rows],
        depot_display_name=depot.display_name,
        depot_lat=depot.lat,
        depot_lon=depot.lon,
    )
