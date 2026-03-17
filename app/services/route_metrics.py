from __future__ import annotations

import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RoutePlan, RouteTrip


def estimate_duration_minutes(distance_km: float, avg_speed_kmh: float = 25.0) -> float:
    return (distance_km / avg_speed_kmh) * 60 if avg_speed_kmh > 0 else 0.0


def estimate_fuel_liters(distance_km: float, km_per_liter: float = 8.0) -> float:
    return distance_km / km_per_liter if km_per_liter > 0 else 0.0


def estimate_co2_kg(fuel_liters: float, kg_per_liter: float = 2.68) -> float:
    return fuel_liters * kg_per_liter


async def get_latest_route_impact(session: AsyncSession) -> dict | None:
    latest_plan_id = await session.scalar(select(func.max(RoutePlan.id)))
    if not latest_plan_id:
        return None

    plan = await session.get(RoutePlan, latest_plan_id)
    if not plan:
        return None

    trips_result = await session.execute(
        select(RouteTrip).where(RouteTrip.plan_id == latest_plan_id)
    )
    trips = trips_result.scalars().all()

    total_stops = 0
    for trip in trips:
        try:
            stops = json.loads(trip.stops_json or "[]")
        except Exception:
            stops = []
        total_stops += len(stops)

    trip_count = len(trips)
    avg_stops_per_trip = (total_stops / trip_count) if trip_count else 0.0

    # simple baseline: assume naive routing is 25% worse
    baseline_distance_km = round(plan.total_distance_km * 1.25, 2)
    distance_saved_km = round(max(0.0, baseline_distance_km - plan.total_distance_km), 2)
    distance_saved_pct = round((distance_saved_km / baseline_distance_km) * 100, 2) if baseline_distance_km > 0 else 0.0

    estimated_duration_minutes = round(estimate_duration_minutes(plan.total_distance_km), 2)
    estimated_fuel_liters = round(estimate_fuel_liters(plan.total_distance_km), 2)
    estimated_co2_kg = round(estimate_co2_kg(estimated_fuel_liters), 2)

    capacity_utilization_pct = round(min(100.0, (total_stops / max(1.0, plan.capacity)) * 100), 2)

    return {
        "plan_id": plan.id,
        "strategy": plan.strategy,
        "total_distance_km": round(plan.total_distance_km, 2),
        "baseline_distance_km": baseline_distance_km,
        "distance_saved_km": distance_saved_km,
        "distance_saved_pct": distance_saved_pct,
        "trip_count": trip_count,
        "total_stops": total_stops,
        "avg_stops_per_trip": round(avg_stops_per_trip, 2),
        "estimated_duration_minutes": estimated_duration_minutes,
        "estimated_fuel_liters": estimated_fuel_liters,
        "estimated_co2_kg": estimated_co2_kg,
        "capacity_utilization_pct": capacity_utilization_pct,
    }