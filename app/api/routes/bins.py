from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_org_context, get_current_user, require_org_permission
from app.db.models import Site, User, Zone
from app.db.session import get_session
from app.repositories.bins import create_bin, delete_bin, get_bin, list_bins, update_bin
from app.repositories.users import get_accessible_bin_ids
from app.schemas.common import BinCreate, BinOut
from app.services.geocoding import GeocodingError, GeocodingService, postcode_sector_from_postcode

router = APIRouter(tags=['bins'])


def _map_bin(record) -> BinOut:
    return BinOut(
        bin_id=record.bin_id,
        name=getattr(record, 'name', None),
        organisation_id=getattr(record, 'organisation_id', None),
        site_id=getattr(record, 'site_id', None),
        zone_id=getattr(record, 'zone_id', None),
        postcode=record.postcode,
        sector=getattr(record, 'sector', None),
        address_line_1=getattr(record, 'address_line_1', None),
        address_line_2=getattr(record, 'address_line_2', None),
        city=getattr(record, 'city', None),
        county=getattr(record, 'county', None),
        country=getattr(record, 'country', None),
        formatted_address=getattr(record, 'formatted_address', None),
        geocode_place_id=getattr(record, 'geocode_place_id', None),
        geocode_source=getattr(record, 'geocode_source', None),
        geocode_confidence=getattr(record, 'geocode_confidence', None),
        lat=record.lat,
        lon=record.lon,
        active=record.active,
        collection_interval_days=getattr(record, 'collection_interval_days', 7),
        collection_weekday=getattr(record, 'collection_weekday', None),
        created_at=record.created_at,
    )


async def _resolve_bin_location(req: BinCreate):
    try:
        resolved = await GeocodingService.resolve(
            place_id=req.geocode_place_id,
            postcode=req.postcode,
            address_line_1=req.address_line_1,
            address_line_2=req.address_line_2,
            city=req.city,
            county=req.county,
            country=req.country,
            formatted_address=req.formatted_address,
            lat=req.lat,
            lon=req.lon,
            allow_manual_override=req.allow_manual_override,
        )
    except GeocodingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolved


@router.post('/bins', response_model=BinOut)
async def create(
    req: BinCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    ctx = await get_active_org_context(session, user, req.organisation_id)
    if ctx.role not in {'manager', 'admin', 'owner'}:
        raise HTTPException(status_code=403, detail='Only manager/admin/owner can create bins')
    await require_org_permission(session, user, req.organisation_id, 'bin:write')

    site = await session.get(Site, req.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail='Site not found')
    if site.organisation_id != req.organisation_id:
        raise HTTPException(status_code=400, detail='site_id does not belong to organisation_id')

    if req.zone_id is not None:
        zone = await session.get(Zone, req.zone_id)
        if zone is None:
            raise HTTPException(status_code=404, detail='Zone not found')
        if zone.site_id != req.site_id:
            raise HTTPException(status_code=400, detail='zone_id does not belong to site_id')

    resolved = await _resolve_bin_location(req)
    record = await create_bin(
        session=session,
        organisation_id=req.organisation_id,
        site_id=req.site_id,
        zone_id=req.zone_id,
        name=req.name,
        postcode=resolved.postcode or req.postcode,
        sector=req.sector or postcode_sector_from_postcode(resolved.postcode or req.postcode),
        address_line_1=resolved.address_line_1 or req.address_line_1,
        address_line_2=resolved.address_line_2 or req.address_line_2,
        city=resolved.city or req.city,
        county=resolved.county or req.county,
        country=resolved.country or req.country,
        formatted_address=resolved.display_name or req.formatted_address,
        geocode_place_id=resolved.place_id or req.geocode_place_id,
        geocode_source=resolved.source or req.geocode_source,
        geocode_confidence=resolved.confidence if resolved.confidence is not None else req.geocode_confidence,
        lat=resolved.lat,
        lon=resolved.lon,
        active=req.active,
        collection_interval_days=req.collection_interval_days,
        collection_weekday=req.collection_weekday,
    )
    return _map_bin(record)


@router.get('/bins', response_model=list[BinOut])
async def list_all(
    organisation_id: int | None = Query(default=None),
    site_id: int | None = Query(default=None),
    zone_id: int | None = Query(default=None),
    postcode: str | None = None,
    sector: str | None = Query(default=None),
    active: bool | None = True,
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    bins = await list_bins(session, organisation_id=organisation_id, site_id=site_id, zone_id=zone_id, postcode=postcode, sector=sector, active=active, limit=limit)
    allowed_bin_ids = await get_accessible_bin_ids(session, user)
    if allowed_bin_ids is not None:
        allowed = set(allowed_bin_ids)
        bins = [item for item in bins if item.bin_id in allowed]
    return [_map_bin(item) for item in bins]


@router.get('/bins/{bin_id}', response_model=BinOut)
async def get_one(
    bin_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = await get_bin(session, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail='Bin not found')
    allowed_bin_ids = await get_accessible_bin_ids(session, user)
    if allowed_bin_ids is not None and bin_id not in set(allowed_bin_ids):
        raise HTTPException(status_code=403, detail='You do not have access to this bin')
    return _map_bin(record)


@router.patch('/bins/{bin_id}', response_model=BinOut)
async def patch_bin(
    bin_id: str,
    req: BinCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_org_permission(session, user, req.organisation_id, 'bin:write')
    site = await session.get(Site, req.site_id)
    if site is None or site.organisation_id != req.organisation_id:
        raise HTTPException(status_code=400, detail='Invalid site/organisation')
    if req.zone_id is not None:
        zone = await session.get(Zone, req.zone_id)
        if zone is None or zone.site_id != req.site_id:
            raise HTTPException(status_code=400, detail='Invalid zone/site')

    resolved = await _resolve_bin_location(req)
    record = await update_bin(
        session,
        bin_id,
        organisation_id=req.organisation_id,
        site_id=req.site_id,
        zone_id=req.zone_id,
        name=req.name,
        postcode=resolved.postcode or req.postcode,
        sector=req.sector or postcode_sector_from_postcode(resolved.postcode or req.postcode),
        address_line_1=resolved.address_line_1 or req.address_line_1,
        address_line_2=resolved.address_line_2 or req.address_line_2,
        city=resolved.city or req.city,
        county=resolved.county or req.county,
        country=resolved.country or req.country,
        formatted_address=resolved.display_name or req.formatted_address,
        geocode_place_id=resolved.place_id or req.geocode_place_id,
        geocode_source=resolved.source or req.geocode_source,
        geocode_confidence=resolved.confidence if resolved.confidence is not None else req.geocode_confidence,
        lat=resolved.lat,
        lon=resolved.lon,
        active=req.active,
        collection_interval_days=req.collection_interval_days,
        collection_weekday=req.collection_weekday,
    )
    if record is None:
        raise HTTPException(status_code=404, detail='Bin not found')
    return _map_bin(record)


@router.delete('/bins/{bin_id}')
async def remove_bin(
    bin_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = await get_bin(session, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail='Bin not found')
    await require_org_permission(session, user, record.organisation_id, 'bin:write')
    ok = await delete_bin(session, bin_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Bin not found')
    return {'ok': True}
