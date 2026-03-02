from __future__ import annotations

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import DecisionRun, DecisionItem

async def create_run(session: AsyncSession, postcode_filter: str | None) -> DecisionRun:
    r = DecisionRun(postcode_filter=postcode_filter)
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r

async def add_item(
    session: AsyncSession,
    run_id: int,
    bin_id: str,
    predicted_class: str,
    confidence: float,
    uncertainty: float,
    current_fill: float,
    predicted_fill_6h: float,
    last_collection_hours: float,
    priority_score: float,
    alerts: list[str],
) -> DecisionItem:
    item = DecisionItem(
        run_id=run_id,
        bin_id=bin_id,
        predicted_class=predicted_class,
        confidence=confidence,
        uncertainty=uncertainty,
        current_fill=current_fill,
        predicted_fill_6h=predicted_fill_6h,
        last_collection_hours=last_collection_hours,
        priority_score=priority_score,
        alerts_json=json.dumps(alerts),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

async def latest_run(session: AsyncSession) -> DecisionRun | None:
    res = await session.execute(select(DecisionRun).order_by(desc(DecisionRun.ts)).limit(1))
    return res.scalar_one_or_none()

async def list_items_for_run(session: AsyncSession, run_id: int) -> list[DecisionItem]:
    res = await session.execute(select(DecisionItem).where(DecisionItem.run_id == run_id).order_by(desc(DecisionItem.priority_score)))
    return list(res.scalars().all())


async def latest_run_with_items(session: AsyncSession):
    run = await latest_run(session)
    if run is None:
        return None, []
    items = await list_items_for_run(session, run.id)
    return run, items
