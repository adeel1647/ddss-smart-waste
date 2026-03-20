from __future__ import annotations

import json
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DecisionItem, DecisionRun


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


async def create_run_with_items(
    session: AsyncSession,
    *,
    postcode_filter: str | None,
    items: list[dict],
) -> tuple[DecisionRun, list[DecisionItem]]:
    run = DecisionRun(postcode_filter=postcode_filter)
    session.add(run)
    await session.flush()

    rows: list[DecisionItem] = []
    for payload in items:
        row = DecisionItem(
            run_id=run.id,
            bin_id=payload['bin_id'],
            predicted_class=payload['predicted_class'],
            confidence=float(payload['confidence']),
            uncertainty=float(payload['uncertainty']),
            current_fill=float(payload['current_fill']),
            predicted_fill_6h=float(payload['predicted_fill_6h']),
            last_collection_hours=float(payload['last_collection_hours']),
            priority_score=float(payload['priority_score']),
            alerts_json=json.dumps(payload.get('alerts', [])),
        )
        rows.append(row)

    session.add_all(rows)
    await session.flush()
    return run, rows


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
