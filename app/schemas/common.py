from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator, field_validator

from app.services.geocoding import normalize_postcode, postcode_sector_from_postcode


class BinCreate(BaseModel):
    organisation_id: int
    site_id: int
    zone_id: int | None = None
    name: str | None = Field(default=None, max_length=120)
    postcode: str | None = Field(default=None, max_length=16)
    sector: str | None = Field(default=None, max_length=64)
    address_line_1: str | None = Field(default=None, max_length=160)
    address_line_2: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=80)
    county: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default='United Kingdom', max_length=80)
    formatted_address: str | None = Field(default=None, max_length=255)
    geocode_place_id: str | None = Field(default=None, max_length=120)
    geocode_source: str | None = Field(default=None, max_length=32)
    geocode_confidence: float | None = Field(default=None, ge=0.0)
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    active: bool = True
    collection_interval_days: int = Field(default=7, ge=1, le=30)
    collection_weekday: int | None = Field(default=None, ge=0, le=6)
    allow_manual_override: bool = False

    @field_validator('postcode', 'sector', 'address_line_1', 'address_line_2', 'city', 'county', 'country', 'formatted_address', 'geocode_place_id', 'geocode_source')
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode='after')
    def validate_location_input(self):
        has_coords = self.lat is not None and self.lon is not None
        has_address = any([
            self.postcode,
            self.formatted_address,
            self.address_line_1,
            self.geocode_place_id,
        ])
        if not has_coords and not has_address:
            raise ValueError('Provide either lat/lon or an address/postcode to locate the bin')
        if has_coords != (self.lon is not None):
            raise ValueError('Both lat and lon are required when manual coordinates are supplied')
        if not self.sector and self.postcode:
            self.sector = postcode_sector_from_postcode(self.postcode)
        self.postcode = normalize_postcode(self.postcode)
        return self


class BinOut(BaseModel):
    bin_id: str
    name: str | None = None
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    postcode: str | None = None
    sector: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    formatted_address: str | None = None
    geocode_place_id: str | None = None
    geocode_source: str | None = None
    geocode_confidence: float | None = None
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
