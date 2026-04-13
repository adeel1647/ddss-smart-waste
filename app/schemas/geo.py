from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AddressSuggestionOut(BaseModel):
    place_id: str
    display_name: str
    formatted_address: str
    lat: float
    lon: float
    postcode: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    source: str = 'nominatim'
    confidence: float | None = None


class AddressSearchResponse(BaseModel):
    query: str
    items: list[AddressSuggestionOut]


class AddressResolveIn(BaseModel):
    place_id: str | None = None
    query: str | None = None
    postcode: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    formatted_address: str | None = None
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    allow_manual_override: bool = False

    @field_validator('place_id', 'query', 'postcode', 'address_line_1', 'address_line_2', 'city', 'county', 'country', 'formatted_address')
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AddressResolveOut(BaseModel):
    place_id: str | None = None
    display_name: str
    lat: float
    lon: float
    postcode: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    source: str = 'nominatim'
    confidence: float | None = None
