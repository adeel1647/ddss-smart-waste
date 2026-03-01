from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BinBase(BaseModel):
    bin_id: str
    sector: Optional[str] = None
    lat: float
    lon: float
    active: bool = True

class BinCreate(BinBase):
    pass

class BinOut(BinBase):
    created_at: datetime

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
