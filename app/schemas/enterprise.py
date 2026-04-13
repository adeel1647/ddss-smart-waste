from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator, field_validator

from app.services.geocoding import normalize_postcode

MembershipRole = Literal['viewer', 'operator', 'manager', 'admin', 'owner']


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
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = 'United Kingdom'
    formatted_address: str | None = None
    geocode_place_id: str | None = None
    geocode_source: str | None = None
    geocode_confidence: float | None = Field(default=None, ge=0.0)
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    allow_manual_override: bool = False

    @field_validator('code', 'address', 'postcode', 'address_line_1', 'address_line_2', 'city', 'county', 'country', 'formatted_address', 'geocode_place_id', 'geocode_source')
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode='after')
    def validate_location_input(self):
        has_coords = self.lat is not None and self.lon is not None
        has_address = any([self.postcode, self.address, self.formatted_address, self.address_line_1, self.geocode_place_id])
        if not has_coords and not has_address:
            raise ValueError('Provide either lat/lon or an address/postcode to locate the site')
        self.postcode = normalize_postcode(self.postcode)
        return self


class SiteOut(BaseModel):
    id: int
    organisation_id: int
    name: str
    code: str | None = None
    address: str | None = None
    postcode: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    formatted_address: str | None = None
    geocode_place_id: str | None = None
    geocode_source: str | None = None
    geocode_confidence: float | None = None
    lat: float | None = None
    lon: float | None = None
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
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    county: str | None = None
    country: str | None = None
    formatted_address: str | None = None
    geocode_place_id: str | None = None
    geocode_source: str | None = None
    geocode_confidence: float | None = Field(default=None, ge=0.0)
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    is_active: bool | None = None
    allow_manual_override: bool = False

    @field_validator('code', 'address', 'postcode', 'address_line_1', 'address_line_2', 'city', 'county', 'country', 'formatted_address', 'geocode_place_id', 'geocode_source')
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


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
