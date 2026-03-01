from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class Point(BaseModel):
    id: str
    lat: float
    lon: float
    priority: float = Field(ge=0.0)
    demand: float = Field(default=0.0, ge=0.0)

class RoutingRequest(BaseModel):
    depot_lat: float
    depot_lon: float
    capacity: float = Field(default=300.0, ge=0.0)
    strategy: Literal["priority_only", "priority_distance"] = "priority_distance"
    points: List[Point]

class Trip(BaseModel):
    stops: List[str]
    trip_distance_km: float

class RoutingResponse(BaseModel):
    strategy: str
    total_distance_km: float
    trips: List[Trip]

class PlanLatestRequest(BaseModel):
    depot_lat: float
    depot_lon: float
    capacity: float = Field(default=300.0, ge=0.0)
    strategy: Literal["priority_only", "priority_distance"] = "priority_distance"
    decision_run_id: Optional[int] = None
    top_n: int = Field(default=50, ge=1, le=2000)

class PlanLatestResponse(BaseModel):
    plan_id: int
    ts: datetime
    decision_run_id: int
    strategy: str
    total_distance_km: float
    trips: List[Trip]
