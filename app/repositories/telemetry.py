from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Telemetry


async def add_telemetry(session: AsyncSession, bin_id: str, fill_level: float, last_collection_hours: float, ts: datetime | None = None) -> Telemetry:
    t = Telemetry(bin_id=bin_id, fill_level=fill_level, last_collection_hours=last_collection_hours, ts=ts or datetime.now(timezone.utc))
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def latest_telemetry(session: AsyncSession, bin_id: str) -> Telemetry | None:
    q = select(Telemetry).where(Telemetry.bin_id == bin_id).order_by(desc(Telemetry.ts)).limit(1)
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def last_n_fill_levels(session: AsyncSession, bin_id: str, n: int = 3) -> list[float]:
    q = select(Telemetry.fill_level).where(Telemetry.bin_id == bin_id).order_by(desc(Telemetry.ts)).limit(n)
    res = await session.execute(q)
    vals = [float(x) for x in res.scalars().all()]
    return list(reversed(vals))


async def get_latest_telemetry_for_bins(session: AsyncSession, bin_ids: list[str]) -> dict[str, Telemetry]:
    if not bin_ids:
        return {}

    subq = (
        select(Telemetry.bin_id, func.max(Telemetry.ts).label('max_ts'))
        .where(Telemetry.bin_id.in_(bin_ids))
        .group_by(Telemetry.bin_id)
        .subquery()
    )
    result = await session.execute(
        select(Telemetry).join(
            subq,
            (Telemetry.bin_id == subq.c.bin_id) & (Telemetry.ts == subq.c.max_ts),
        )
    )
    rows = result.scalars().all()
    return {row.bin_id: row for row in rows}


async def get_recent_fill_lags_for_bins(session: AsyncSession, bin_ids: list[str], take: int = 3) -> dict[str, list[float]]:
    if not bin_ids:
        return {}

    result = await session.execute(
        select(Telemetry)
        .where(Telemetry.bin_id.in_(bin_ids))
        .order_by(Telemetry.bin_id, desc(Telemetry.ts))
    )
    rows = result.scalars().all()

    grouped: dict[str, list[float]] = {bin_id: [] for bin_id in bin_ids}
    for row in rows:
        bucket = grouped.setdefault(row.bin_id, [])
        if len(bucket) < take:
            bucket.append(float(row.fill_level))
    return grouped
