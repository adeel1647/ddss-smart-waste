from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Bin
from app.services.idgen import next_bin_id

async def create_bin(session: AsyncSession, postcode: str | None, lat: float, lon: float, active: bool):
    bin_id = await next_bin_id(session)
    b = Bin(bin_id=bin_id, postcode=postcode, lat=lat, lon=lon, active=active)
    session.add(b)
    await session.commit()
    await session.refresh(b)
    return b

async def get_bin(session: AsyncSession, bin_id: str) -> Bin | None:
    res = await session.execute(select(Bin).where(Bin.bin_id == bin_id))
    return res.scalar_one_or_none()

async def list_bins(session: AsyncSession, postcode: str | None = None, active: bool | None = True, limit: int = 200) -> list[Bin]:
    q = select(Bin)
    if postcode is not None:
        q = q.where(Bin.postcode == postcode)
    if active is not None:
        q = q.where(Bin.active == active)
    q = q.limit(limit)
    res = await session.execute(q)
    return list(res.scalars().all())
