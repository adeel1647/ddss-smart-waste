from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Literal
from app.utils.geo import haversine_km

@dataclass
class Point:
    id: str
    lat: float
    lon: float
    priority: float
    demand: float

def optimize_capacity_constrained(
    depot_lat: float,
    depot_lon: float,
    points: List[Point],
    capacity: float,
    strategy: Literal["priority_only", "priority_distance"] = "priority_distance",
    epsilon: float = 1e-6,
) -> Tuple[float, List[Dict]]:
    remaining = points[:]
    trips: List[Dict] = []
    total = 0.0

    def dist(a_lat, a_lon, b_lat, b_lon):
        return haversine_km(a_lat, a_lon, b_lat, b_lon)

    while remaining:
        stops = ["DEPOT"]
        trip_km = 0.0
        load = 0.0
        cur_lat, cur_lon = depot_lat, depot_lon

        while True:
            feasible = [p for p in remaining if load + p.demand <= capacity]
            if not feasible:
                break
            if strategy == "priority_only":
                feasible.sort(key=lambda p: p.priority, reverse=True)
                nxt = feasible[0]
            else:
                feasible.sort(key=lambda p: dist(cur_lat, cur_lon, p.lat, p.lon) / (p.priority + epsilon))
                nxt = feasible[0]

            d = dist(cur_lat, cur_lon, nxt.lat, nxt.lon)
            trip_km += d
            total += d
            load += nxt.demand
            stops.append(nxt.id)
            cur_lat, cur_lon = nxt.lat, nxt.lon
            remaining = [p for p in remaining if p.id != nxt.id]

        d_back = dist(cur_lat, cur_lon, depot_lat, depot_lon)
        trip_km += d_back
        total += d_back
        stops.append("DEPOT")
        trips.append({"stops": stops, "trip_distance_km": trip_km, "trip_load": load})

    return total, trips
