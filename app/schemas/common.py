from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------- BINS ----------

class BinCreate(BaseModel):
    postcode: str | None = Field(default=None, max_length=16)
    lat: float
    lon: float
    active: bool = True


class BinOut(BaseModel):
    bin_id: str
    postcode: str | None = None
    lat: float
    lon: float
    active: bool
    created_at: datetime


# ---------- TELEMETRY ----------

class TelemetryCreate(BaseModel):
    ts: Optional[datetime] = None
    fill_level: float
    last_collection_hours: float


class TelemetryOut(BaseModel):
    id: int
    bin_id: str
    ts: datetime
    fill_level: float
    last_collection_hours: float