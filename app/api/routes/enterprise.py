from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, require_roles, get_current_user, require_org_permission
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
    delete_organisation,
    delete_site,
    delete_zone,
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
    update_organisation,
    update_site,
    update_zone,
)
from app.repositories.users import create_membership
from app.schemas.enterprise import (
    AuditLogOut,
    DeviceCreate,
    DeviceHeartbeatIn,
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
    OrganisationUpdate,
    ScheduledReportCreate,
    ScheduledReportOut,
    SiteCreate,
    SiteOut,
    SiteUpdate,
    ZoneCreate,
    ZoneOut,
    ZoneUpdate,
)
from app.services.audit import log_audit
from app.services.geocoding import GeocodingError, GeocodingService

router = APIRouter(prefix='/enterprise', tags=['enterprise'])


def _map_site(row: Site) -> SiteOut:
    return SiteOut(
        id=row.id,
        organisation_id=row.organisation_id,
        name=row.name,
        code=row.code,
        address=row.address,
        postcode=getattr(row, 'postcode', None),
        address_line_1=getattr(row, 'address_line_1', None),
        address_line_2=getattr(row, 'address_line_2', None),
        city=getattr(row, 'city', None),
        county=getattr(row, 'county', None),
        country=getattr(row, 'country', None),
        formatted_address=getattr(row, 'formatted_address', None),
        geocode_place_id=getattr(row, 'geocode_place_id', None),
        geocode_source=getattr(row, 'geocode_source', None),
        geocode_confidence=getattr(row, 'geocode_confidence', None),
        lat=row.lat,
        lon=row.lon,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _resolve_site_location(payload: SiteCreate | SiteUpdate):
    try:
        resolved = await GeocodingService.resolve(
            place_id=payload.geocode_place_id,
            postcode=payload.postcode,
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            county=payload.county,
            country=payload.country,
            formatted_address=payload.formatted_address or payload.address,
            lat=payload.lat,
            lon=payload.lon,
            allow_manual_override=payload.allow_manual_override,
        )
    except GeocodingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolved


@router.get('/organisations', response_model=list[OrganisationOut])
async def get_organisations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    memberships = await list_memberships(session, user_id=user.id)
    roles = {m.role for m in memberships}

    if user.platform_role in {'owner', 'admin'} or 'owner' in roles or 'admin' in roles:
        return await list_organisations(session)

    allowed = {m.organisation_id for m in memberships}
    rows = await list_organisations(session)
    return [row for row in rows if row.id in allowed]


@router.post('/organisations', response_model=OrganisationOut)
async def post_organisation(
    payload: OrganisationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_roles('owner', 'admin')),
):
    row = await create_organisation(
        session,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )

    if user.platform_role == 'owner':
        await create_membership(
            session,
            user_id=user.id,
            organisation_id=row.id,
            role='owner',
            is_default=False,
        )
    elif user.platform_role == 'admin':
        await create_membership(
            session,
            user_id=user.id,
            organisation_id=row.id,
            role='admin',
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
    if user.platform_role in {'owner', 'admin'} or ctx.organisation_id is not None:
        return [_map_site(row) for row in rows]
    memberships = await list_memberships(session, user_id=user.id)
    allowed = {m.organisation_id for m in memberships}
    return [_map_site(row) for row in rows if row.organisation_id in allowed]


@router.post('/sites', response_model=SiteOut)
async def post_site(
    payload: SiteCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, payload.organisation_id, 'site:write')
    resolved = await _resolve_site_location(payload)
    row = await create_site(
        session,
        organisation_id=payload.organisation_id,
        name=payload.name,
        code=payload.code,
        address=payload.address or payload.formatted_address or resolved.display_name,
        postcode=resolved.postcode or payload.postcode,
        address_line_1=resolved.address_line_1 or payload.address_line_1,
        address_line_2=resolved.address_line_2 or payload.address_line_2,
        city=resolved.city or payload.city,
        county=resolved.county or payload.county,
        country=resolved.country or payload.country,
        formatted_address=resolved.display_name or payload.formatted_address or payload.address,
        geocode_place_id=resolved.place_id or payload.geocode_place_id,
        geocode_source=resolved.source or payload.geocode_source,
        geocode_confidence=resolved.confidence if resolved.confidence is not None else payload.geocode_confidence,
        lat=resolved.lat,
        lon=resolved.lon,
    )
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='site.create', entity_type='site', entity_id=str(row.id), details=payload.model_dump())
    await session.commit()
    await session.refresh(row)
    return _map_site(row)


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
    if user.platform_role in {'owner', 'admin'} and ctx.organisation_id is None:
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


@router.patch('/organisations/{organisation_id}', response_model=OrganisationOut)
async def patch_organisation(
    organisation_id: int,
    payload: OrganisationUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if user.platform_role not in {'owner', 'admin'}:
        raise HTTPException(status_code=403, detail='Only owner/admin can edit organisations')
    row = await update_organisation(session, organisation_id, **payload.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail='Organisation not found')
    await log_audit(session, organisation_id=row.id, actor_user_id=user.id, action='organisation.update', entity_type='organisation', entity_id=str(row.id), details=payload.model_dump(exclude_unset=True))
    return row


@router.delete('/organisations/{organisation_id}')
async def remove_organisation(
    organisation_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if user.platform_role != 'owner':
        raise HTTPException(status_code=403, detail='Only owner can delete organisations')
    ok = await delete_organisation(session, organisation_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Organisation not found')
    return {'ok': True}


@router.patch('/sites/{site_id}', response_model=SiteOut)
async def patch_site(
    site_id: int,
    payload: SiteUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = await session.get(Site, site_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Site not found')
    await require_org_permission(session, user, row.organisation_id, 'site:write')

    patch_data = payload.model_dump(exclude_unset=True)
    needs_geocode = any(
        key in patch_data
        for key in {
            'address', 'postcode', 'address_line_1', 'address_line_2', 'city', 'county', 'country',
            'formatted_address', 'geocode_place_id', 'lat', 'lon'
        }
    )
    if needs_geocode:
        merged = SiteCreate(
            organisation_id=row.organisation_id,
            name=patch_data.get('name', row.name),
            code=patch_data.get('code', row.code),
            address=patch_data.get('address', row.address),
            postcode=patch_data.get('postcode', getattr(row, 'postcode', None)),
            address_line_1=patch_data.get('address_line_1', getattr(row, 'address_line_1', None)),
            address_line_2=patch_data.get('address_line_2', getattr(row, 'address_line_2', None)),
            city=patch_data.get('city', getattr(row, 'city', None)),
            county=patch_data.get('county', getattr(row, 'county', None)),
            country=patch_data.get('country', getattr(row, 'country', None)),
            formatted_address=patch_data.get('formatted_address', getattr(row, 'formatted_address', None)),
            geocode_place_id=patch_data.get('geocode_place_id', getattr(row, 'geocode_place_id', None)),
            geocode_source=patch_data.get('geocode_source', getattr(row, 'geocode_source', None)),
            geocode_confidence=patch_data.get('geocode_confidence', getattr(row, 'geocode_confidence', None)),
            lat=patch_data.get('lat', row.lat),
            lon=patch_data.get('lon', row.lon),
            allow_manual_override=patch_data.get('allow_manual_override', False),
        )
        resolved = await _resolve_site_location(merged)
        patch_data.update({
            'address': merged.address or merged.formatted_address or resolved.display_name,
            'postcode': resolved.postcode or merged.postcode,
            'address_line_1': resolved.address_line_1 or merged.address_line_1,
            'address_line_2': resolved.address_line_2 or merged.address_line_2,
            'city': resolved.city or merged.city,
            'county': resolved.county or merged.county,
            'country': resolved.country or merged.country,
            'formatted_address': resolved.display_name or merged.formatted_address,
            'geocode_place_id': resolved.place_id or merged.geocode_place_id,
            'geocode_source': resolved.source or merged.geocode_source,
            'geocode_confidence': resolved.confidence if resolved.confidence is not None else merged.geocode_confidence,
            'lat': resolved.lat,
            'lon': resolved.lon,
        })

    updated = await update_site(session, site_id, **patch_data)
    await log_audit(session, organisation_id=row.organisation_id, actor_user_id=user.id, action='site.update', entity_type='site', entity_id=str(site_id), details=patch_data)
    return _map_site(updated)


@router.delete('/sites/{site_id}')
async def remove_site(site_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    row = await session.get(Site, site_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Site not found')
    await require_org_permission(session, user, row.organisation_id, 'site:write')
    ok = await delete_site(session, site_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Site not found')
    return {'ok': True}


@router.patch('/zones/{zone_id}', response_model=ZoneOut)
async def patch_zone(zone_id: int, payload: ZoneUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    row = await session.get(Zone, zone_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Zone not found')
    site = await session.get(Site, row.site_id)
    await require_org_permission(session, user, site.organisation_id, 'zone:write')
    updated = await update_zone(session, zone_id, **payload.model_dump(exclude_unset=True))
    await log_audit(session, organisation_id=site.organisation_id, actor_user_id=user.id, action='zone.update', entity_type='zone', entity_id=str(zone_id), details=payload.model_dump(exclude_unset=True))
    return updated


@router.delete('/zones/{zone_id}')
async def remove_zone(zone_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    row = await session.get(Zone, zone_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Zone not found')
    site = await session.get(Site, row.site_id)
    await require_org_permission(session, user, site.organisation_id, 'zone:write')
    ok = await delete_zone(session, zone_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Zone not found')
    return {'ok': True}


@router.get('/memberships', response_model=list[MembershipOut])
async def get_memberships(
    organisation_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if organisation_id is not None:
        await require_org_permission(session, user, organisation_id, 'membership:read')
        return await list_memberships(session, organisation_id=organisation_id)
    if user.platform_role in {'owner', 'admin'}:
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
    if payload.role == 'owner' and ctx.role != 'owner' and user.platform_role != 'owner':
        raise HTTPException(status_code=403, detail='Only an owner can assign the owner role')
    if payload.role == 'admin' and ctx.role not in {'owner', 'admin'}:
        raise HTTPException(status_code=403, detail='Only owner or admin can assign admin role')
    if ctx.role == 'admin' and payload.role == 'owner':
        raise HTTPException(status_code=403, detail='Admins cannot promote a member to owner')
    if ctx.role == 'manager' and payload.role not in {'operator', 'viewer'}:
        raise HTTPException(status_code=403, detail='Managers can only assign operator/viewer roles')

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
        actor_email=(getattr(row, 'actor', None).email if getattr(row, 'actor', None) else None),
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        status=row.status,
        details=json.loads(row.details_json or '{}'),
        created_at=row.created_at,
    )
