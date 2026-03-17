from pydantic import BaseModel


class RoutingImpactOut(BaseModel):
    plan_id: int
    strategy: str
    total_distance_km: float
    baseline_distance_km: float
    distance_saved_km: float
    distance_saved_pct: float
    trip_count: int
    total_stops: int
    avg_stops_per_trip: float
    estimated_duration_minutes: float
    estimated_fuel_liters: float
    estimated_co2_kg: float
    capacity_utilization_pct: float