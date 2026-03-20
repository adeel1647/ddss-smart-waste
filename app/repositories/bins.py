from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bin
from app.services.idgen import next_bin_id


async def create_bin(
    session: AsyncSession,
    postcode: str | None,
    sector: str | None,
    lat: float,
    lon: float,
    active: bool,
    collection_interval_days: int,
    collection_weekday: int | None,
) -> Bin:
    bin_id = await next_bin_id(session)
    record = Bin(
        bin_id=bin_id,
        postcode=postcode,
        sector=sector,
        lat=lat,
        lon=lon,
        active=active,
        collection_interval_days=collection_interval_days,
        collection_weekday=collection_weekday,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_bin(session: AsyncSession, bin_id: str) -> Bin | None:
    result = await session.execute(select(Bin).where(Bin.bin_id == bin_id))
    return result.scalar_one_or_none()


async def get_bins_by_ids(session: AsyncSession, bin_ids: list[str]) -> dict[str, Bin]:
    if not bin_ids:
        return {}
    result = await session.execute(select(Bin).where(Bin.bin_id.in_(bin_ids)))
    rows = result.scalars().all()
    return {row.bin_id: row for row in rows}


async def list_bins(
    session: AsyncSession,
    postcode: str | None = None,
    sector: str | None = None,
    active: bool | None = True,
    limit: int = 200,
) -> list[Bin]:
    query = select(Bin)
    if postcode is not None:
        query = query.where(Bin.postcode == postcode)
    if sector is not None:
        query = query.where(Bin.sector == sector)
    if active is not None:
        query = query.where(Bin.active == active)
    query = query.order_by(Bin.created_at.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())
