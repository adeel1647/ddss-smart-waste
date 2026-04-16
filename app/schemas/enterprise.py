from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator, field_validator

from app.services.geocoding import normalize_postcode

MembershipRole = Literal['viewer', 'operator', 'manager', 'admin', 'owner']
GeoJsonPoint = list[float]
GeoJsonRing = list[GeoJsonPoint]
GeoJsonPolygonCoordinates = list[GeoJsonRing]

def validate_polygon_geojson(value: dict | None) -> dict | None:
    if value is None:
        return None

    if value.get("type") != "Polygon":
        raise ValueError("boundary_geojson must be a GeoJSON Polygon")

    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("boundary_geojson.coordinates must be a non-empty list")

    outer_ring = coordinates[0]
    if not isinstance(outer_ring, list) or len(outer_ring) < 4:
        raise ValueError("Polygon outer ring must contain at least 4 points")

    for point in outer_ring:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("Each polygon point must be [lon, lat]")
        lon, lat = point
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            raise ValueError("Polygon coordinates must be numeric")
        if lat < -90 or lat > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if lon < -180 or lon > 180:
            raise ValueError("Longitude must be between -180 and 180")

    if outer_ring[0] != outer_ring[-1]:
        raise ValueError("Polygon ring must be closed")

    return value

class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None


class OrganisationOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SiteCreate(BaseModel):
    organisation_id: int
    name: str
    code: str | None = None
    address: str | None = None
    postcode: str | None = None
    boundary_geojson: dict | None = None

    @field_validator('code', 'address', 'postcode')
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator('boundary_geojson')
    @classmethod
    def validate_boundary(cls, value: dict | None) -> dict | None:
        return validate_polygon_geojson(value)

    @model_validator(mode='after')
    def normalize_values(self):
        self.postcode = normalize_postcode(self.postcode)
        return self

class SiteOut(BaseModel):
    id: int
    organisation_id: int
    name: str
    code: str | None = None
    address: str | None = None
    postcode: str | None = None
    lat: float | None = None
    lon: float | None = None
    boundary_geojson: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ZoneCreate(BaseModel):
    site_id: int
    name: str
    code: str | None = None
    service_level: str | None = None


class ZoneOut(BaseModel):
    id: int
    site_id: int
    name: str
    code: str | None = None
    service_level: str | None = None
    created_at: datetime
    updated_at: datetime


class OrganisationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SiteUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    postcode: str | None = None
    boundary_geojson: dict | None = None
    is_active: bool | None = None

    @field_validator('code', 'address', 'postcode')
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator('boundary_geojson')
    @classmethod
    def validate_boundary(cls, value: dict | None) -> dict | None:
        return validate_polygon_geojson(value)

    @model_validator(mode='after')
    def normalize_values(self):
        self.postcode = normalize_postcode(self.postcode)
        return self

class ZoneUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    service_level: str | None = None


class MembershipCreate(BaseModel):
    organisation_id: int
    user_id: int
    role: MembershipRole = 'viewer'
    is_default: bool = False


class MembershipOut(BaseModel):
    id: int
    organisation_id: int
    user_id: int
    role: MembershipRole
    is_default: bool
    created_at: datetime


class DeviceCreate(BaseModel):
    organisation_id: int
    site_id: int | None = None
    zone_id: int | None = None
    bin_id: str | None = None
    serial_number: str
    device_type: str = 'sensor'
    firmware_version: str | None = None
    battery_pct: float | None = None
    maintenance_due_at: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class DeviceOut(BaseModel):
    id: int
    organisation_id: int
    site_id: int | None = None
    zone_id: int | None = None
    bin_id: str | None = None
    serial_number: str
    device_type: str
    firmware_version: str | None = None
    battery_pct: float | None = None
    status: str
    installed_at: datetime | None = None
    last_seen_at: datetime | None = None
    maintenance_due_at: datetime | None = None
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DeviceHeartbeatIn(BaseModel):
    battery_pct: float | None = None
    rssi: float | None = None
    temperature_c: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DeviceHeartbeatOut(BaseModel):
    id: int
    device_id: int
    ts: datetime
    battery_pct: float | None = None
    rssi: float | None = None
    temperature_c: float | None = None
    payload: dict[str, Any]


class NotificationChannelCreate(BaseModel):
    organisation_id: int
    name: str
    channel_type: Literal['email', 'sms', 'webhook', 'in_app'] = 'email'
    target: str
    enabled: bool = True
    severity_filter: Literal['info', 'warning', 'critical'] | None = None
    event_types: list[str] = Field(default_factory=list)


class NotificationChannelOut(BaseModel):
    id: int
    organisation_id: int
    name: str
    channel_type: str
    target: str
    enabled: bool
    severity_filter: str | None = None
    event_types: list[str]
    created_at: datetime


class NotificationEventCreate(BaseModel):
    organisation_id: int
    channel_id: int | None = None
    alert_id: int | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class NotificationEventOut(BaseModel):
    id: int
    organisation_id: int
    channel_id: int | None = None
    alert_id: int | None = None
    event_type: str
    status: str
    payload: dict[str, Any]
    created_at: datetime
    sent_at: datetime | None = None


class ScheduledReportCreate(BaseModel):
    organisation_id: int
    name: str
    report_type: str = 'ops_summary'
    cron_expr: str
    format: Literal['csv', 'pdf', 'json'] = 'csv'
    recipients: list[str] = Field(default_factory=list)
    enabled: bool = True


class ScheduledReportOut(BaseModel):
    id: int
    organisation_id: int
    name: str
    report_type: str
    cron_expr: str
    format: str
    recipients: list[str]
    enabled: bool
    last_run_at: datetime | None = None
    created_at: datetime


class AuditLogOut(BaseModel):
    id: int
    organisation_id: int | None = None
    actor_user_id: int | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    status: str
    details: dict[str, Any]
    created_at: datetime
