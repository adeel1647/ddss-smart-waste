from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

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
    lat: float | None = None
    lon: float | None = None


class SiteOut(BaseModel):
    id: int
    organisation_id: int
    name: str
    code: str | None = None
    address: str | None = None
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
    action: str
    entity_type: str
    entity_id: str | None = None
    status: str
    details: dict[str, Any]
    created_at: datetime
