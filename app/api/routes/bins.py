from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_default_membership
from app.db.models import User
from app.db.session import get_session
from app.repositories.bins import create_bin, get_bin, list_bins
from app.repositories.users import get_accessible_bin_ids
from app.schemas.common import BinCreate, BinOut

router = APIRouter(tags=['bins'])


def _map_bin(record) -> BinOut:
    return BinOut(
        bin_id=record.bin_id,
        postcode=record.postcode,
        sector=getattr(record, 'sector', None),
        lat=record.lat,
        lon=record.lon,
        active=record.active,
        collection_interval_days=getattr(record, 'collection_interval_days', 7),
        collection_weekday=getattr(record, 'collection_weekday', None),
        created_at=record.created_at,
    )


async def _active_role(session: AsyncSession, user: User) -> str:
    membership = await get_default_membership(session, user.id)
    return 'owner' if user.is_admin else (membership.role if membership else 'viewer')


@router.post('/bins', response_model=BinOut)
async def create(
    req: BinCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    role = await _active_role(session, user)
    if role not in {'manager', 'admin', 'owner'}:
        raise HTTPException(status_code=403, detail='Only manager/admin/owner can create bins')
    record = await create_bin(
        session,
        req.postcode,
        req.sector,
        req.lat,
        req.lon,
        req.active,
        req.collection_interval_days,
        req.collection_weekday,
    )
    return _map_bin(record)


@router.get('/bins', response_model=list[BinOut])
async def list_all(
    postcode: str | None = None,
    sector: str | None = Query(default=None),
    active: bool | None = True,
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    bins = await list_bins(session, postcode=postcode, sector=sector, active=active, limit=limit)
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
