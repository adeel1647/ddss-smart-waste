from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator, field_validator

from app.services.geocoding import normalize_postcode


class Point(BaseModel):
    id: str
    lat: float
    lon: float
    priority: float = Field(ge=0.0)
    demand: float = Field(default=0.0, ge=0.0)


class DepotLocationIn(BaseModel):
    depot_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    depot_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    depot_postcode: str | None = None
    depot_address: str | None = None
    depot_place_id: str | None = None
    depot_address_line_1: str | None = None
    depot_address_line_2: str | None = None
    depot_city: str | None = None
    depot_county: str | None = None
    depot_country: str | None = 'United Kingdom'

    @field_validator('depot_postcode', 'depot_address', 'depot_place_id', 'depot_address_line_1', 'depot_address_line_2', 'depot_city', 'depot_county', 'depot_country')
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode='after')
    def validate_depot(self):
        has_coords = self.depot_lat is not None and self.depot_lon is not None
        has_address = any([
            self.depot_postcode,
            self.depot_address,
            self.depot_place_id,
            self.depot_address_line_1,
        ])
        if not has_coords and not has_address:
            raise ValueError('Provide either depot_lat/depot_lon or a depot address/postcode')
        if has_coords != (self.depot_lon is not None):
            raise ValueError('Both depot_lat and depot_lon are required when coordinates are supplied')
        self.depot_postcode = normalize_postcode(self.depot_postcode)
        return self


class RoutingRequest(DepotLocationIn):
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
    depot_display_name: str | None = None
    depot_lat: float
    depot_lon: float


class PlanLatestRequest(DepotLocationIn):
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
    depot_display_name: str | None = None
    depot_lat: float
    depot_lon: float


class PlanLatestVrpRequest(DepotLocationIn):
    capacity: int = Field(ge=1, description='Vehicle capacity in demand units')
    max_vehicles: int = Field(default=6, ge=1, le=20)
    top_n: int = Field(default=50, ge=1, le=500)
    priority_weight: float = Field(default=10.0, ge=0.0, le=500.0)
    use_osrm: bool = Field(default=True, description='Fetch road geometry via OSRM (may be rate-limited)')
