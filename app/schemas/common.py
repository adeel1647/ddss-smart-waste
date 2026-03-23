from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BinCreate(BaseModel):
    organisation_id: int
    site_id: int
    zone_id: int | None = None
    name: str | None = Field(default=None, max_length=120)
    postcode: str | None = Field(default=None, max_length=16)
    sector: str | None = Field(default=None, max_length=64)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    active: bool = True
    collection_interval_days: int = Field(default=7, ge=1, le=30)
    collection_weekday: int | None = Field(default=None, ge=0, le=6)

    @field_validator('postcode', 'sector')
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BinOut(BaseModel):
    bin_id: str
    name: str | None = None
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    postcode: str | None = None
    sector: str | None = None
    lat: float
    lon: float
    active: bool
    collection_interval_days: int
    collection_weekday: int | None = None
    created_at: datetime


class TelemetryCreate(BaseModel):
    ts: datetime | None = None
    fill_level: float = Field(ge=0.0, le=100.0)
    last_collection_hours: float = Field(ge=0.0, le=8760.0)


class TelemetryOut(BaseModel):
    id: int
    bin_id: str
    ts: datetime
    fill_level: float
    last_collection_hours: float
