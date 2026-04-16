from __future__ import annotations

from typing import Iterable


def point_in_ring(lat: float, lon: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1

    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]   # lon, lat
        xj, yj = ring[j][0], ring[j][1]

        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside

        j = i

    return inside


def point_in_polygon_geojson(lat: float, lon: float, polygon: dict | None) -> bool:
    if not polygon or polygon.get("type") != "Polygon":
        return False

    coordinates = polygon.get("coordinates") or []
    if not coordinates:
        return False

    outer_ring = coordinates[0]
    if not point_in_ring(lat, lon, outer_ring):
        return False

    # holes
    for hole in coordinates[1:]:
        if point_in_ring(lat, lon, hole):
            return False

    return True