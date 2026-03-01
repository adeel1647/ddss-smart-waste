from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import Classification

async def add_classification(session: AsyncSession, bin_id: str, predicted_class: str, confidence: float, ts: datetime | None = None) -> Classification:
    c = Classification(bin_id=bin_id, predicted_class=predicted_class, confidence=confidence, ts=ts or datetime.utcnow())
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c

async def latest_classification(session: AsyncSession, bin_id: str) -> Classification | None:
    q = select(Classification).where(Classification.bin_id == bin_id).order_by(desc(Classification.ts)).limit(1)
    res = await session.execute(q)
    return res.scalar_one_or_none()
