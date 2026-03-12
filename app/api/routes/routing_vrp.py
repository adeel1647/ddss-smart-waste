from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_session
from app.repositories.decisions import latest_run, list_items_for_run
from app.repositories.bins import get_bin
from app.repositories.routes import create_plan, add_trip, trips_for_plan

from app.services.routing_vrp import VrpNode, solve_vrp


router = APIRouter(tags=["routing"])


class PlanLatestVrpRequest(BaseModel):
    depot_lat: float
    depot_lon: float
    capacity: int = Field(ge=1, description="Vehicle capacity in demand units")
    max_vehicles: int = Field(default=6, ge=1, le=20)
    top_n: int = Field(default=50, ge=1, le=500)
    priority_weight: float = Field(default=10.0, ge=0.0, le=500.0)
    use_osrm: bool = Field(default=True, description="Fetch road geometry via OSRM (may be rate-limited)")


@router.post("/routing/plan-latest-vrp")
async def plan_latest_vrp(req: PlanLatestVrpRequest, session: AsyncSession = Depends(get_session)):
    # 1) Latest DDSS run
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail="No decision run found (run /ddss/run first).")

    items = await list_items_for_run(session, run.id)
    items = items[: req.top_n]

    # 2) Build VRP nodes (DEPOT first)
    nodes: list[VrpNode] = [
        VrpNode(key="DEPOT", lat=req.depot_lat, lon=req.depot_lon, demand=0, priority=0.0)
    ]

    total_demand = 0
    for it in items:
        b = await get_bin(session, it.bin_id)
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
        raise HTTPException(status_code=400, detail="No routable points (bins must have locations and DDSS items).")

    # 3) Choose vehicle count based on demand/capacity (bounded)
    vehicles = max(1, min(req.max_vehicles, (total_demand + req.capacity - 1) // req.capacity))

    # 4) Solve VRP (optionally OSRM geometry)
    result = await solve_vrp(
        nodes=nodes,
        vehicle_capacity=req.capacity,
        vehicles=vehicles,
        priority_weight=req.priority_weight,
        use_osrm_geometry=req.use_osrm,
    )

    # 5) Persist plan like your existing plan_latest does
    plan = await create_plan(
        session=session,
        decision_run_id=run.id,
        strategy="vrp",
        capacity=req.capacity,
        depot_lat=req.depot_lat,
        depot_lon=req.depot_lon,
        total_distance_km=float(result["total_distance_km"]),
    )

    # Save trips (store stops; also store geometry if your DB supports it)
    # If your trip table only has stops_json + trip_distance_km, we store only stops.
    for idx, t in enumerate(result["trips"]):
        await add_trip(
            session,
            plan_id=plan.id,
            trip_index=idx,
            stops=t["stops"],
            trip_distance_km=float(t["trip_distance_km"]),
        )

    stored = await trips_for_plan(session, plan.id)
    out_trips = []
    # Attach geometry from solver output to response (even if not stored)
    # Map by trip_index.
    geometry_by_index = {i: result["trips"][i].get("geometry") for i in range(len(result["trips"]))}

    for tr in stored:
        stops = json.loads(tr.stops_json)
        out_trips.append(
            {
                "stops": stops,
                "trip_distance_km": float(tr.trip_distance_km),
                "geometry": geometry_by_index.get(tr.trip_index),
            }
        )

    return {
        "plan_id": plan.id,
        "ts": plan.ts,
        "decision_run_id": run.id,
        "strategy": "vrp",
        "total_distance_km": float(result["total_distance_km"]),
        "trips": out_trips,
    }