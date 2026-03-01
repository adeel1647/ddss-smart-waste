from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import Telemetry

async def add_telemetry(session: AsyncSession, bin_id: str, fill_level: float, last_collection_hours: float, ts: datetime | None = None) -> Telemetry:
    t = Telemetry(bin_id=bin_id, fill_level=fill_level, last_collection_hours=last_collection_hours, ts=ts or datetime.utcnow())
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
