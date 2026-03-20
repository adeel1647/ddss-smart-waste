from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Device,
    DeviceHeartbeat,
    NotificationChannel,
    NotificationEvent,
    Organisation,
    OrganisationMembership,
    ScheduledReport,
    Site,
    Zone,
)


async def create_organisation(
    session: AsyncSession,
    *,
    name: str,
    slug: str | None,
    description: str | None,
) -> Organisation:
    row = Organisation(name=name, slug=slug or "", description=description)
    session.add(row)
    await session.flush()
    return row


async def list_organisations(session: AsyncSession) -> list[Organisation]:
    result = await session.execute(select(Organisation).order_by(Organisation.name.asc()))
    return list(result.scalars().all())


async def create_site(session: AsyncSession, **kwargs) -> Site:
    row = Site(**kwargs)
    session.add(row)
    await session.flush()
    return row


async def list_sites(session: AsyncSession, organisation_id: int | None = None) -> list[Site]:
    stmt = select(Site)
    if organisation_id is not None:
        stmt = stmt.where(Site.organisation_id == organisation_id)
    stmt = stmt.order_by(Site.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_zone(session: AsyncSession, **kwargs) -> Zone:
    row = Zone(**kwargs)
    session.add(row)
    await session.flush()
    return row


async def list_zones(session: AsyncSession, site_id: int | None = None) -> list[Zone]:
    stmt = select(Zone)
    if site_id is not None:
        stmt = stmt.where(Zone.site_id == site_id)
    stmt = stmt.order_by(Zone.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_membership(session: AsyncSession, **kwargs) -> OrganisationMembership:
    row = OrganisationMembership(**kwargs)
    session.add(row)
    await session.flush()
    return row


async def list_memberships(session: AsyncSession, organisation_id: int | None = None, user_id: int | None = None) -> list[OrganisationMembership]:
    stmt = select(OrganisationMembership)
    if organisation_id is not None:
        stmt = stmt.where(OrganisationMembership.organisation_id == organisation_id)
    if user_id is not None:
        stmt = stmt.where(OrganisationMembership.user_id == user_id)
    stmt = stmt.order_by(OrganisationMembership.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_device(session: AsyncSession, **kwargs) -> Device:
    meta = kwargs.pop('meta', {})
    row = Device(**kwargs, meta_json=json.dumps(meta))
    session.add(row)
    await session.flush()
    return row


async def list_devices(session: AsyncSession, organisation_id: int | None = None, status: str | None = None) -> list[Device]:
    stmt = select(Device)
    if organisation_id is not None:
        stmt = stmt.where(Device.organisation_id == organisation_id)
    if status:
        stmt = stmt.where(Device.status == status)
    stmt = stmt.order_by(Device.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_device(session: AsyncSession, device_id: int) -> Device | None:
    return await session.get(Device, device_id)


async def create_device_heartbeat(session: AsyncSession, *, device: Device, battery_pct: float | None, rssi: float | None, temperature_c: float | None, payload: dict) -> DeviceHeartbeat:
    ts = datetime.now(timezone.utc)
    if battery_pct is not None:
        device.battery_pct = battery_pct
    device.last_seen_at = ts
    device.status = 'online'
    row = DeviceHeartbeat(
        device_id=device.id,
        ts=ts,
        battery_pct=battery_pct,
        rssi=rssi,
        temperature_c=temperature_c,
        payload_json=json.dumps(payload or {}),
    )
    session.add(row)
    await session.flush()
    return row


async def create_notification_channel(session: AsyncSession, **kwargs) -> NotificationChannel:
    event_types = kwargs.pop('event_types', [])
    row = NotificationChannel(**kwargs, event_types_json=json.dumps(event_types))
    session.add(row)
    await session.flush()
    return row


async def list_notification_channels(session: AsyncSession, organisation_id: int | None = None) -> list[NotificationChannel]:
    stmt = select(NotificationChannel)
    if organisation_id is not None:
        stmt = stmt.where(NotificationChannel.organisation_id == organisation_id)
    stmt = stmt.order_by(NotificationChannel.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_notification_event(session: AsyncSession, **kwargs) -> NotificationEvent:
    payload = kwargs.pop('payload', {})
    row = NotificationEvent(**kwargs, payload_json=json.dumps(payload or {}))
    session.add(row)
    await session.flush()
    return row


async def list_notification_events(session: AsyncSession, organisation_id: int | None = None) -> list[NotificationEvent]:
    stmt = select(NotificationEvent)
    if organisation_id is not None:
        stmt = stmt.where(NotificationEvent.organisation_id == organisation_id)
    stmt = stmt.order_by(NotificationEvent.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_scheduled_report(session: AsyncSession, **kwargs) -> ScheduledReport:
    recipients = kwargs.pop('recipients', [])
    row = ScheduledReport(**kwargs, recipients_json=json.dumps(recipients))
    session.add(row)
    await session.flush()
    return row


async def list_scheduled_reports(session: AsyncSession, organisation_id: int | None = None) -> list[ScheduledReport]:
    stmt = select(ScheduledReport)
    if organisation_id is not None:
        stmt = stmt.where(ScheduledReport.organisation_id == organisation_id)
    stmt = stmt.order_by(ScheduledReport.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_audit_log(session: AsyncSession, **kwargs) -> AuditLog:
    details = kwargs.pop('details', {})
    row = AuditLog(**kwargs, details_json=json.dumps(details or {}))
    session.add(row)
    await session.flush()
    return row


async def list_audit_logs(
    session: AsyncSession,
    organisation_id: int | None = None,
    entity_type: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if organisation_id is not None:
        stmt = stmt.where(AuditLog.organisation_id == organisation_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
