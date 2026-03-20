from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bin, Classification, ContaminationCase, Device, ModelMetricSnapshot, Telemetry


async def list_candidate_bins(session: AsyncSession, organisation_id: int | None = None, limit: int = 200) -> list[Bin]:
    stmt = select(Bin).where(Bin.active.is_(True))
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    stmt = stmt.order_by(Bin.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_latest_telemetry_map(session: AsyncSession, bin_ids: list[str]) -> dict[str, Telemetry]:
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


async def get_latest_classification_map(session: AsyncSession, bin_ids: list[str]) -> dict[str, Classification]:
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


async def get_recent_telemetry_series(session: AsyncSession, bin_ids: list[str], hours: int = 48) -> dict[str, list[Telemetry]]:
    if not bin_ids:
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await session.execute(
        select(Telemetry)
        .where(Telemetry.bin_id.in_(bin_ids), Telemetry.ts >= cutoff)
        .order_by(Telemetry.bin_id.asc(), Telemetry.ts.asc())
    )
    rows = result.scalars().all()
    grouped: dict[str, list[Telemetry]] = {bin_id: [] for bin_id in bin_ids}
    for row in rows:
        grouped.setdefault(row.bin_id, []).append(row)
    return grouped


async def get_device_status_map(session: AsyncSession, bin_ids: list[str]) -> dict[str, list[Device]]:
    if not bin_ids:
        return {}
    result = await session.execute(select(Device).where(Device.bin_id.in_(bin_ids)).order_by(Device.created_at.desc()))
    rows = result.scalars().all()
    grouped: dict[str, list[Device]] = {bin_id: [] for bin_id in bin_ids}
    for row in rows:
        if row.bin_id:
            grouped.setdefault(row.bin_id, []).append(row)
    return grouped


async def create_contamination_case(session: AsyncSession, **kwargs) -> ContaminationCase:
    evidence = kwargs.pop('evidence', {})
    row = ContaminationCase(**kwargs, evidence_json=json.dumps(evidence or {}))
    session.add(row)
    await session.flush()
    return row


async def update_contamination_case(session: AsyncSession, row: ContaminationCase, **kwargs) -> ContaminationCase:
    if 'evidence' in kwargs and kwargs['evidence'] is not None:
        row.evidence_json = json.dumps(kwargs.pop('evidence') or {})
    for key, value in kwargs.items():
        if value is not None:
            setattr(row, key, value)
    if row.status in {'resolved', 'dismissed'} and row.resolved_at is None:
        row.resolved_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def get_contamination_case(session: AsyncSession, case_id: int) -> ContaminationCase | None:
    return await session.get(ContaminationCase, case_id)


async def list_contamination_cases(session: AsyncSession, organisation_id: int | None = None, status: str | None = None, limit: int = 100) -> list[ContaminationCase]:
    stmt = select(ContaminationCase)
    if organisation_id is not None:
        stmt = stmt.where(ContaminationCase.organisation_id == organisation_id)
    if status:
        stmt = stmt.where(ContaminationCase.status == status)
    stmt = stmt.order_by(ContaminationCase.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_model_metric_snapshot(session: AsyncSession, **kwargs) -> ModelMetricSnapshot:
    meta = kwargs.pop('meta', {})
    row = ModelMetricSnapshot(**kwargs, meta_json=json.dumps(meta or {}))
    session.add(row)
    await session.flush()
    return row


async def list_model_metric_snapshots(session: AsyncSession, model_name: str | None = None, days: int = 14, limit: int = 200) -> list[ModelMetricSnapshot]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(ModelMetricSnapshot).where(ModelMetricSnapshot.created_at >= cutoff)
    if model_name:
        stmt = stmt.where(ModelMetricSnapshot.model_name == model_name)
    stmt = stmt.order_by(ModelMetricSnapshot.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
