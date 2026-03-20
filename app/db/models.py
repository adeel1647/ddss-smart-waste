from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Column, Index, Integer, String, Text, UniqueConstraint, func, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify_text(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or 'organisation'


class Base(DeclarativeBase):
    pass


class Organisation(Base):
    __tablename__ = 'organisations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true', nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    sites: Mapped[List['Site']] = relationship(back_populates='organisation', cascade='all, delete-orphan')
    memberships: Mapped[List['OrganisationMembership']] = relationship(back_populates='organisation', cascade='all, delete-orphan')
    notification_channels: Mapped[List['NotificationChannel']] = relationship(back_populates='organisation', cascade='all, delete-orphan')
    report_schedules: Mapped[List['ScheduledReport']] = relationship(back_populates='organisation', cascade='all, delete-orphan')
    devices: Mapped[List['Device']] = relationship(back_populates='organisation')
    audit_logs: Mapped[List['AuditLog']] = relationship(back_populates='organisation')


class Site(Base):
    __tablename__ = 'sites'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true', nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    organisation: Mapped['Organisation'] = relationship(back_populates='sites')
    zones: Mapped[List['Zone']] = relationship(back_populates='site', cascade='all, delete-orphan')
    bins: Mapped[List['Bin']] = relationship(back_populates='site')
    devices: Mapped[List['Device']] = relationship(back_populates='site')

    __table_args__ = (UniqueConstraint('organisation_id', 'name', name='uq_sites_org_name'),)


class Zone(Base):
    __tablename__ = 'zones'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    service_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    site: Mapped['Site'] = relationship(back_populates='zones')
    bins: Mapped[List['Bin']] = relationship(back_populates='zone')
    devices: Mapped[List['Device']] = relationship(back_populates='zone')

    __table_args__ = (UniqueConstraint('site_id', 'name', name='uq_zones_site_name'),)


class Bin(Base):
    __tablename__ = 'bins'

    bin_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), nullable=True, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey('sites.id', ondelete='SET NULL'), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey('zones.id', ondelete='SET NULL'), nullable=True, index=True)
    postcode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    sector: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true', nullable=False, index=True)
    collection_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default='7')
    collection_weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    site: Mapped['Site | None'] = relationship(back_populates='bins')
    zone: Mapped['Zone | None'] = relationship(back_populates='bins')
    telemetry: Mapped[List['Telemetry']] = relationship(back_populates='bin', cascade='all, delete-orphan')
    classifications: Mapped[List['Classification']] = relationship(back_populates='bin', cascade='all, delete-orphan')
    devices: Mapped[List['Device']] = relationship(back_populates='bin')


class Telemetry(Base):
    __tablename__ = 'telemetry'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    fill_level: Mapped[float] = mapped_column(Float, nullable=False)
    last_collection_hours: Mapped[float] = mapped_column(Float, nullable=False)

    bin: Mapped['Bin'] = relationship(back_populates='telemetry')

    __table_args__ = (Index('ix_telemetry_bin_ts', 'bin_id', 'ts'),)


class Classification(Base):
    __tablename__ = 'classifications'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    bin: Mapped['Bin'] = relationship(back_populates='classifications')

    __table_args__ = (Index('ix_classifications_bin_ts', 'bin_id', 'ts'),)


class DecisionRun(Base):
    __tablename__ = 'decision_runs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    postcode_filter: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    items: Mapped[List['DecisionItem']] = relationship(back_populates='run', cascade='all, delete-orphan')


class DecisionItem(Base):
    __tablename__ = 'decision_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('decision_runs.id', ondelete='CASCADE'), index=True)
    bin_id: Mapped[str] = mapped_column(String(64), index=True)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    current_fill: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_fill_6h: Mapped[float] = mapped_column(Float, nullable=False)
    last_collection_hours: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    alerts_json: Mapped[str] = mapped_column(String, nullable=False, default='[]')

    run: Mapped['DecisionRun'] = relationship(back_populates='items')


class RoutePlan(Base):
    __tablename__ = 'route_plans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    decision_run_id: Mapped[int] = mapped_column(Integer, index=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False)
    depot_lat: Mapped[float] = mapped_column(Float, nullable=False)
    depot_lon: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    trips: Mapped[List['RouteTrip']] = relationship(back_populates='plan', cascade='all, delete-orphan')


class RouteTrip(Base):
    __tablename__ = 'route_trips'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey('route_plans.id', ondelete='CASCADE'), index=True)
    trip_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stops_json: Mapped[str] = mapped_column(String, nullable=False)
    trip_distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    plan: Mapped['RoutePlan'] = relationship(back_populates='trips')


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memberships: Mapped[List['OrganisationMembership']] = relationship(back_populates='user', cascade='all, delete-orphan')
    site_assignments: Mapped[List['UserSiteAssignment']] = relationship(back_populates='user', cascade='all, delete-orphan')
    bin_assignments: Mapped[List['UserBinAssignment']] = relationship(back_populates='user', cascade='all, delete-orphan')


class OrganisationMembership(Base):
    __tablename__ = 'organisation_memberships'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default='viewer', server_default='viewer', index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    organisation: Mapped['Organisation'] = relationship(back_populates='memberships')
    user: Mapped['User'] = relationship(back_populates='memberships')

    __table_args__ = (UniqueConstraint('organisation_id', 'user_id', name='uq_membership_org_user'),)




class UserSiteAssignment(Base):
    __tablename__ = 'user_site_assignments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    user: Mapped['User'] = relationship(back_populates='site_assignments')
    site: Mapped['Site'] = relationship()

    __table_args__ = (UniqueConstraint('user_id', 'site_id', name='uq_user_site_assignment'),)


class UserBinAssignment(Base):
    __tablename__ = 'user_bin_assignments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    user: Mapped['User'] = relationship(back_populates='bin_assignments')
    bin: Mapped['Bin'] = relationship()

    __table_args__ = (UniqueConstraint('user_id', 'bin_id', name='uq_user_bin_assignment'),)


class PasswordResetCode(Base):
    __tablename__ = 'password_reset_codes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped['User'] = relationship()


class Alert(Base):
    __tablename__ = 'alerts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), index=True)
    decision_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey('decision_runs.id', ondelete='SET NULL'), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='open', index=True)
    meta_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    bin: Mapped['Bin'] = relationship()
    decision_run: Mapped[Optional['DecisionRun']] = relationship()

    __table_args__ = (Index('ix_alerts_bin_status_created', 'bin_id', 'status', 'created_at'),)


class WorkOrder(Base):
    __tablename__ = 'work_orders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), index=True)
    alert_id: Mapped[Optional[int]] = mapped_column(ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True, index=True)
    route_plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey('route_plans.id', ondelete='SET NULL'), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default='medium', index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='open', index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    bin: Mapped['Bin'] = relationship()
    alert: Mapped[Optional['Alert']] = relationship()
    route_plan: Mapped[Optional['RoutePlan']] = relationship()

    __table_args__ = (Index('ix_work_orders_status_priority_due', 'status', 'priority', 'due_at'),)


class Device(Base):
    __tablename__ = 'devices'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey('sites.id', ondelete='SET NULL'), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey('zones.id', ondelete='SET NULL'), nullable=True, index=True)
    bin_id: Mapped[str | None] = mapped_column(ForeignKey('bins.bin_id', ondelete='SET NULL'), nullable=True, index=True)
    serial_number: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    device_type: Mapped[str] = mapped_column(String(60), nullable=False, default='sensor')
    firmware_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='provisioned', index=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    maintenance_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    organisation: Mapped['Organisation'] = relationship(back_populates='devices')
    site: Mapped['Site | None'] = relationship(back_populates='devices')
    zone: Mapped['Zone | None'] = relationship(back_populates='devices')
    bin: Mapped['Bin | None'] = relationship(back_populates='devices')
    heartbeats: Mapped[List['DeviceHeartbeat']] = relationship(back_populates='device', cascade='all, delete-orphan')


class DeviceHeartbeat(Base):
    __tablename__ = 'device_heartbeats'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    rssi: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')

    device: Mapped['Device'] = relationship(back_populates='heartbeats')


class NotificationChannel(Base):
    __tablename__ = 'notification_channels'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(24), nullable=False, default='email')
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    severity_filter: Mapped[str | None] = mapped_column(String(24), nullable=True)
    event_types_json: Mapped[str] = mapped_column(String, nullable=False, default='[]')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organisation: Mapped['Organisation'] = relationship(back_populates='notification_channels')
    events: Mapped[List['NotificationEvent']] = relationship(back_populates='channel', cascade='all, delete-orphan')


class NotificationEvent(Base):
    __tablename__ = 'notification_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey('notification_channels.id', ondelete='SET NULL'), nullable=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='queued', index=True)
    payload_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    channel: Mapped['NotificationChannel | None'] = relationship(back_populates='events')


class ScheduledReport(Base):
    __tablename__ = 'scheduled_reports'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    report_type: Mapped[str] = mapped_column(String(60), nullable=False, default='ops_summary')
    cron_expr: Mapped[str] = mapped_column(String(120), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default='csv')
    recipients_json: Mapped[str] = mapped_column(String, nullable=False, default='[]')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organisation: Mapped['Organisation'] = relationship(back_populates='report_schedules')


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='success', index=True)
    details_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    organisation: Mapped['Organisation | None'] = relationship(back_populates='audit_logs')


class ContaminationCase(Base):
    __tablename__ = 'contamination_cases'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), nullable=True, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey('sites.id', ondelete='SET NULL'), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey('zones.id', ondelete='SET NULL'), nullable=True, index=True)
    bin_id: Mapped[str] = mapped_column(ForeignKey('bins.bin_id', ondelete='CASCADE'), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False, default='manual')
    contamination_type: Mapped[str] = mapped_column(String(80), nullable=False, default='mixed_waste')
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default='medium', index=True)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='open', index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_contamination_cases_org_status_created', 'organisation_id', 'status', 'created_at'),
    )


class ModelMetricSnapshot(Base):
    __tablename__ = 'model_metric_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    window_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='ok', index=True)
    meta_json: Mapped[str] = mapped_column(String, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('ix_model_metric_snapshots_model_metric_created', 'model_name', 'metric_name', 'created_at'),
    )



@event.listens_for(Organisation, 'before_insert')
def _organisation_before_insert(mapper, connection, target: Organisation) -> None:
    if not target.slug:
        target.slug = slugify_text(target.name)
    if not target.created_at:
        target.created_at = utcnow()
    if not target.updated_at:
        target.updated_at = utcnow()


@event.listens_for(Organisation, 'before_update')
def _organisation_before_update(mapper, connection, target: Organisation) -> None:
    if not target.slug:
        target.slug = slugify_text(target.name)
    target.updated_at = utcnow()
