from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, require_roles, get_current_user, get_user_memberships, require_admin, require_org_permission
from app.db.models import OrganisationMembership, Site, User, Zone
from app.db.session import get_session
from app.repositories.enterprise import (
    create_device,
    create_device_heartbeat,
    create_notification_channel,
    create_notification_event,
    create_organisation,
    create_scheduled_report,
    create_site,
    create_zone,
    get_device,
    list_audit_logs,
    list_devices,
    list_memberships,
    list_notification_channels,
    list_notification_events,
    list_organisations,
    list_scheduled_reports,
    list_sites,
    list_zones,
)
from app.repositories.users import create_membership
from app.schemas.enterprise import (
    AuditLogOut,
    DeviceCreate,
    DeviceHeartbeatIn,
    # create_membership,
    DeviceHeartbeatOut,
    DeviceOut,
    MembershipCreate,
    MembershipOut,
    NotificationChannelCreate,
    NotificationChannelOut,
    NotificationEventCreate,
    NotificationEventOut,
    OrganisationCreate,
    OrganisationOut,
    ScheduledReportCreate,
    ScheduledReportOut,
    SiteCreate,
    SiteOut,
    ZoneCreate,
    ZoneOut,
)
from app.services.audit import log_audit

router = APIRouter(prefix='/enterprise', tags=['enterprise'])


@router.get('/organisations', response_model=list[OrganisationOut])
async def get_organisations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    memberships = await list_memberships(session, user_id=user.id)
    roles = {m.role for m in memberships}

    if user.is_admin or 'owner' in roles:
        return await list_organisations(session)

    allowed = {m.organisation_id for m in memberships}
    rows = await list_organisations(session)
    return [row for row in rows if row.id in allowed]


@router.post('/organisations', response_model=OrganisationOut)
async def post_organisation(
    payload: OrganisationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_roles("owner", "admin")),
):
    row = await create_organisation(
        session,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )

    await create_membership(
        session,
        user_id=user.id,
        organisation_id=row.id,
        role="owner",
        is_default=False,
    )

    await log_audit(
        session,
        organisation_id=row.id,
        actor_user_id=user.id,
        action='organisation.create',
        entity_type='organisation',
        entity_id=str(row.id),
        details=payload.model_dump(),
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.get('/sites', response_model=list[SiteOut])
async def get_sites(
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'site:read')
    rows = await list_sites(session, organisation_id=ctx.organisation_id)
    if user.is_admin or ctx.organisation_id is not None:
        return rows
    memberships = await list_memberships(session, user_id=user.id)
    allowed = {m.organisation_id for m in memberships}
    return [row for row in rows if row.organisation_id in allowed]


@router.post('/sites', response_model=SiteOut)
async def post_site(
    payload: SiteCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'site:write')
    row = await create_site(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='site.create', entity_type='site', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return row


@router.get('/zones', response_model=list[ZoneOut])
async def get_zones(
    site_id: int | None = Query(default=None),
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if site_id is not None:
        site = await session.get(Site, site_id)
        if site is None:
            raise HTTPException(status_code=404, detail='Site not found')
        await require_org_permission(session, user, site.organisation_id, 'zone:read')
        rows = await list_zones(session, site_id=site_id)
        return rows
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'zone:read')
    rows = await list_zones(session, site_id=None)
    if user.is_admin or ctx.organisation_id is None:
        if user.is_admin:
            return rows
    site_rows = await list_sites(session, organisation_id=ctx.organisation_id if ctx.organisation_id is not None else None)
    allowed_site_ids = {row.id for row in site_rows}
    return [row for row in rows if row.site_id in allowed_site_ids]


@router.post('/zones', response_model=ZoneOut)
async def post_zone(
    payload: ZoneCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    site = await session.get(Site, payload.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail='Site not found')
    await require_org_permission(session, user, site.organisation_id, 'zone:write')
    row = await create_zone(session, **payload.model_dump())
    await log_audit(session, organisation_id=site.organisation_id, actor_user_id=user.id, action='zone.create', entity_type='zone', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return row


@router.get('/memberships', response_model=list[MembershipOut])
async def get_memberships(
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if organisation_id is not None:
        await require_org_permission(session, user, organisation_id, 'membership:read')
        return await list_memberships(session, organisation_id=organisation_id)
    if user.is_admin:
        return await list_memberships(session)
    return await list_memberships(session, user_id=user.id)


@router.post('/memberships', response_model=MembershipOut)
async def post_membership(
    payload: MembershipCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, payload.organisation_id)
    await require_org_permission(session, user, payload.organisation_id, 'membership:write')
    if payload.role == 'owner' and ctx.role != 'owner' and not user.is_admin:
        raise HTTPException(status_code=403, detail='Only an owner can assign the owner role')
    if payload.role == 'admin' and ctx.role not in {'owner', 'admin', 'platform_admin'}:
        raise HTTPException(status_code=403, detail='Only owner or admin can assign admin role')
    if ctx.role == 'admin' and payload.role == 'owner':
        raise HTTPException(status_code=403, detail='Admins cannot promote a member to owner')

    if payload.is_default:
        await session.execute(
            update(OrganisationMembership)
            .where(OrganisationMembership.user_id == payload.user_id)
            .values(is_default=False)
        )
    row = await create_membership(session, **payload.model_dump())
    await log_audit(session, organisation_id=payload.organisation_id, actor_user_id=user.id, action='membership.create', entity_type='membership', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return row


@router.get('/devices', response_model=list[DeviceOut])
async def get_devices(
    organisation_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, organisation_id)
    if ctx.organisation_id is not None:
        await require_org_permission(session, user, ctx.organisation_id, 'device:read')
    rows = await list_devices(session, organisation_id=ctx.organisation_id, status=status)
    if user.is_admin or ctx.organisation_id is not None:
        return [_map_device(row) for row in rows]
    memberships = await list_memberships(session, user_id=user.id)
    allowed = {m.organisation_id for m in memberships}
    return [_map_device(row) for row in rows if row.organisation_id in allowed]


@router.post('/devices', response_model=DeviceOut)
async def post_device(
    payload: DeviceCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'device:write')
    row = await create_device(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='device.create', entity_type='device', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_device(row)


@router.post('/devices/{device_id}/heartbeat', response_model=DeviceHeartbeatOut)
async def post_device_heartbeat(
    device_id: int,
    payload: DeviceHeartbeatIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    device = await get_device(session, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail='Device not found')
    await require_org_permission(session, user, device.organisation_id, 'device:heartbeat')
    row = await create_device_heartbeat(session, device=device, **payload.model_dump())
    await log_audit(session, organisation_id=device.organisation_id, actor_user_id=user.id, action='device.heartbeat', entity_type='device', entity_id=str(device.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return DeviceHeartbeatOut(
        id=row.id,
        device_id=row.device_id,
        ts=row.ts,
        battery_pct=row.battery_pct,
        rssi=row.rssi,
        temperature_c=row.temperature_c,
        payload=json.loads(row.payload_json or '{}'),
    )


@router.get('/notification-channels', response_model=list[NotificationChannelOut])
async def get_notification_channels(
    organisation_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, organisation_id, 'notification:read')
    rows = await list_notification_channels(session, organisation_id=organisation_id)
    return [_map_channel(row) for row in rows]


@router.post('/notification-channels', response_model=NotificationChannelOut)
async def post_notification_channel(
    payload: NotificationChannelCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'notification:write')
    row = await create_notification_channel(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='notification_channel.create', entity_type='notification_channel', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_channel(row)


@router.get('/notification-events', response_model=list[NotificationEventOut])
async def get_notification_events(
    organisation_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, organisation_id, 'notification:read')
    rows = await list_notification_events(session, organisation_id=organisation_id)
    return [_map_event(row) for row in rows]


@router.post('/notification-events', response_model=NotificationEventOut)
async def post_notification_event(
    payload: NotificationEventCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'notification:write')
    row = await create_notification_event(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='notification_event.create', entity_type='notification_event', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_event(row)


@router.get('/reports', response_model=list[ScheduledReportOut])
async def get_reports(
    organisation_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, organisation_id, 'report:read')
    rows = await list_scheduled_reports(session, organisation_id=organisation_id)
    return [_map_report(row) for row in rows]


@router.post('/reports', response_model=ScheduledReportOut)
async def post_report(
    payload: ScheduledReportCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'report:write')
    row = await create_scheduled_report(session, **payload.model_dump())
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='report_schedule.create', entity_type='scheduled_report', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_report(row)


@router.get('/audit-logs', response_model=list[AuditLogOut])
async def get_audit_logs(
    organisation_id: int,
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, organisation_id, 'audit:read')
    rows = await list_audit_logs(session, organisation_id=organisation_id, entity_type=entity_type, limit=limit)
    return [_map_audit(row) for row in rows]


def _map_device(row) -> DeviceOut:
    return DeviceOut(
        id=row.id,
        organisation_id=row.organisation_id,
        site_id=row.site_id,
        zone_id=row.zone_id,
        bin_id=row.bin_id,
        serial_number=row.serial_number,
        device_type=row.device_type,
        firmware_version=row.firmware_version,
        battery_pct=row.battery_pct,
        status=row.status,
        installed_at=row.installed_at,
        last_seen_at=row.last_seen_at,
        maintenance_due_at=row.maintenance_due_at,
        meta=json.loads(row.meta_json or '{}'),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _map_channel(row) -> NotificationChannelOut:
    return NotificationChannelOut(
        id=row.id,
        organisation_id=row.organisation_id,
        name=row.name,
        channel_type=row.channel_type,
        target=row.target,
        enabled=row.enabled,
        severity_filter=row.severity_filter,
        event_types=json.loads(row.event_types_json or '[]'),
        created_at=row.created_at,
    )


def _map_event(row) -> NotificationEventOut:
    return NotificationEventOut(
        id=row.id,
        organisation_id=row.organisation_id,
        channel_id=row.channel_id,
        alert_id=row.alert_id,
        event_type=row.event_type,
        status=row.status,
        payload=json.loads(row.payload_json or '{}'),
        created_at=row.created_at,
        sent_at=row.sent_at,
    )


def _map_report(row) -> ScheduledReportOut:
    return ScheduledReportOut(
        id=row.id,
        organisation_id=row.organisation_id,
        name=row.name,
        report_type=row.report_type,
        cron_expr=row.cron_expr,
        format=row.format,
        recipients=json.loads(row.recipients_json or '[]'),
        enabled=row.enabled,
        last_run_at=row.last_run_at,
        created_at=row.created_at,
    )


def _map_audit(row) -> AuditLogOut:
    return AuditLogOut(
        id=row.id,
        organisation_id=row.organisation_id,
        actor_user_id=row.actor_user_id,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        status=row.status,
        details=json.loads(row.details_json or '{}'),
        created_at=row.created_at,
    )

# @router.post("/memberships")
# async def create_membership(
#     payload: MembershipCreate,
#     db: AsyncSession = Depends(get_session),
#     membership = Depends(require_roles("owner", "admin")),
# ):
#     if payload.role == "owner" and membership.role != "owner":
#         raise HTTPException(403, "Only owner can assign owner")

#     new_m = OrganisationMembership(
#         organisation_id=payload.organisation_id,
#         user_id=payload.user_id,
#         role=payload.role,
#         is_default=True,
#     )

#     db.add(new_m)
#     await db.commit()

#     return {"message": "Membership created"}