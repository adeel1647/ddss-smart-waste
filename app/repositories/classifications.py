from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Classification


async def add_classification(session: AsyncSession, bin_id: str, predicted_class: str, confidence: float, ts: datetime | None = None) -> Classification:
    c = Classification(bin_id=bin_id, predicted_class=predicted_class, confidence=confidence, ts=ts or datetime.now(timezone.utc))
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


async def latest_classification(session: AsyncSession, bin_id: str) -> Classification | None:
    q = select(Classification).where(Classification.bin_id == bin_id).order_by(desc(Classification.ts)).limit(1)
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def get_latest_classifications_for_bins(session: AsyncSession, bin_ids: list[str]) -> dict[str, Classification]:
    if not bin_ids:
        return {}

    subq = (
        select(Classification.bin_id, func.max(Classification.ts).label('max_ts'))
        .where(Classification.bin_id.in_(bin_ids))
        .group_by(Classification.bin_id)
        .subquery()
    )
    result = await session.execute(
        select(Classification).join(
            subq,
            (Classification.bin_id == subq.c.bin_id) & (Classification.ts == subq.c.max_ts),
        )
    )
    rows = result.scalars().all()
    return {row.bin_id: row for row in rows}
