from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import httpx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


@dataclass
class VrpNode:
    key: str  # "DEPOT" or bin_id
    lat: float
    lon: float
    demand: int  # capacity demand units (integer)
    priority: float  # ddss priority score (float)


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    # (lat, lon)
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def build_distance_matrix_km(nodes: List[VrpNode]) -> List[List[float]]:
    n = len(nodes)
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                mat[i][j] = 0.0
            else:
                mat[i][j] = haversine_km((nodes[i].lat, nodes[i].lon), (nodes[j].lat, nodes[j].lon))
    return mat


def km_to_cost(km: float) -> int:
    # OR-Tools requires integer costs; use meters-like scaling
    return int(round(km * 1000))


OSRM_BASE_URL = "http://router.project-osrm.org"
OSRM_TIMEOUT = 20.0

async def osrm_route_geojson(coords_lonlat: List[Tuple[float, float]]) -> Optional[List[Tuple[float, float]]]:
    """
    coords_lonlat: [(lon,lat), (lon,lat), ...]
    returns [(lat,lon), ...]
    """
    if len(coords_lonlat) < 2:
        return None

    coord_str = ";".join([f"{lon},{lat}" for (lon, lat) in coords_lonlat])
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coord_str}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
        # "continue_straight": "false",  # optional
    }

    async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            # Log the reason (VERY useful)
            try:
                print("OSRM error", r.status_code, r.text[:300])
            except Exception:
                pass
            return None

        data = r.json()
        routes = data.get("routes", [])
        if not routes:
            return None

        points = routes[0]["geometry"]["coordinates"]  # [[lon,lat],...]
        return [(lat, lon) for lon, lat in points]

async def osrm_route_for_stops(nodes_by_key: Dict[str, VrpNode], stops: List[str]) -> Optional[List[Tuple[float, float]]]:
    if len(stops) < 2:
        return None

    full: List[Tuple[float, float]] = []

    for i in range(len(stops) - 1):
        a = nodes_by_key[stops[i]]
        b = nodes_by_key[stops[i + 1]]

        seg = await osrm_route_geojson([(a.lon, a.lat), (b.lon, b.lat)])
        if not seg or len(seg) < 2:
            return None

        if full:
            seg = seg[1:]  # avoid duplicate join point
        full.extend(seg)

    return full

async def solve_vrp(
    nodes: List[VrpNode],
    vehicle_capacity: int,
    vehicles: int,
    priority_weight: float = 0.0,
    use_osrm_geometry: bool = False,
) -> Dict:
    """
    nodes[0] must be DEPOT.
    - vehicle_capacity: total demand per vehicle/trip
    - vehicles: number of vehicles/trips solver can use
    - priority_weight: optional bias to visit high-priority bins earlier (soft)
    - use_osrm_geometry: if True, fetch road geometry for each trip
    """
    if not nodes or nodes[0].key != "DEPOT":
        raise ValueError("nodes must start with DEPOT")

    dist_km = build_distance_matrix_km(nodes)
    dist_cost = [[km_to_cost(x) for x in row] for row in dist_km]

    manager = pywrapcp.RoutingIndexManager(len(nodes), vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Distance callback (objective)
    def distance_cb(from_index: int, to_index: int) -> int:
        f = manager.IndexToNode(from_index)
        t = manager.IndexToNode(to_index)
        base = dist_cost[f][t]
        # Soft bias: reduce cost slightly when heading toward high-priority nodes (encourages earlier visit)
        # Note: keep it small to avoid breaking distance optimization.
        if priority_weight > 0.0 and t != 0:
            bonus = int(min(5000, nodes[t].priority * priority_weight))  # cap bonus
            base = max(0, base - bonus)
        return base

    transit_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # Capacity (demand) constraint
    def demand_cb(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        return nodes[node].demand

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx,
        0,
        [vehicle_capacity] * vehicles,
        True,
        "Capacity",
    )

    # Search settings
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(3)

    solution = routing.SolveWithParameters(params)
    if solution is None:
        raise RuntimeError("VRP solver failed to find a solution.")

    # Extract trips
    trips = []
    total_km = 0.0

    for v in range(vehicles):
        idx = routing.Start(v)
        route_nodes = []
        route_km = 0.0

        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            route_nodes.append(node)

            nxt = solution.Value(routing.NextVar(idx))
            nxt_node = manager.IndexToNode(nxt)

            route_km += dist_km[node][nxt_node]
            idx = nxt

        # add final depot
        route_nodes.append(manager.IndexToNode(idx))

        stops = [nodes[i].key for i in route_nodes]

        # skip empty routes (DEPOT → DEPOT)
        if stops == ["DEPOT", "DEPOT"]:
            continue

        total_km += route_km

        geometry = None
        if use_osrm_geometry:
            try:
                nodes_by_key = {n.key: n for n in nodes}
                geometry = await osrm_route_for_stops(nodes_by_key, stops)
            except Exception as e:
                print("OSRM geometry error:", e)
                geometry = None

        trips.append(
            {
                "stops": stops,
                "trip_distance_km": round(route_km, 2),
                "geometry": geometry,
            }
        )

    return {
        "total_distance_km": round(total_km, 2),
        "trips": trips,
    }