from __future__ import annotations

from datetime import datetime, timedelta, timezone, time
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Bin, Classification, RoutePlan, Telemetry


async def get_analytics_overview(session: AsyncSession, organisation_id: int | None = None) -> dict:
    now = datetime.now(timezone.utc)
    start_of_today = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    telemetry_stmt = (
        select(func.avg(Telemetry.fill_level))
        .select_from(Telemetry)
        .join(Bin, Bin.bin_id == Telemetry.bin_id)
        .where(Telemetry.ts >= start_of_today)
    )

    max_fill_stmt = (
        select(func.max(Telemetry.fill_level))
        .select_from(Telemetry)
        .join(Bin, Bin.bin_id == Telemetry.bin_id)
        .where(Telemetry.ts >= start_of_today)
    )

    critical_stmt = (
        select(func.count())
        .select_from(Alert)
        .join(Bin, Bin.bin_id == Alert.bin_id)
        .where(Alert.created_at >= start_of_today, Alert.severity == 'critical')
    )

    open_stmt = (
        select(func.count())
        .select_from(Alert)
        .join(Bin, Bin.bin_id == Alert.bin_id)
        .where(Alert.status == 'open')
    )

    class_stmt = (
        select(Classification.predicted_class)
        .select_from(Classification)
        .join(Bin, Bin.bin_id == Classification.bin_id)
        .where(Classification.ts >= start_of_today)
    )

    route_stmt = select(RoutePlan.total_distance_km).order_by(RoutePlan.ts.desc()).limit(1)
    if organisation_id is not None:
        telemetry_stmt = telemetry_stmt.where(Bin.organisation_id == organisation_id)
        max_fill_stmt = max_fill_stmt.where(Bin.organisation_id == organisation_id)
        critical_stmt = critical_stmt.where(Bin.organisation_id == organisation_id)
        open_stmt = open_stmt.where(Bin.organisation_id == organisation_id)
        class_stmt = class_stmt.where(Bin.organisation_id == organisation_id)
        route_stmt = (
            select(RoutePlan.total_distance_km)
            .where(RoutePlan.organisation_id == organisation_id)
            .order_by(RoutePlan.ts.desc())
            .limit(1)
        )

    avg_fill_today = float((await session.scalar(telemetry_stmt)) or 0.0)
    max_fill_today = float((await session.scalar(max_fill_stmt)) or 0.0)
    critical_alerts_today = int((await session.scalar(critical_stmt)) or 0)
    open_alerts_total = int((await session.scalar(open_stmt)) or 0)
    latest_route_distance_km = float((await session.scalar(route_stmt)) or 0.0)

    top_waste_class_today = await session.scalar(
        class_stmt.group_by(Classification.predicted_class).order_by(func.count().desc()).limit(1)
    )

    return {
        'avg_fill_today': round(avg_fill_today, 2),
        'max_fill_today': round(max_fill_today, 2),
        'critical_alerts_today': critical_alerts_today,
        'open_alerts_total': open_alerts_total,
        'latest_route_distance_km': round(latest_route_distance_km, 2),
        'top_waste_class_today': top_waste_class_today,
    }

async def get_fill_trend(session: AsyncSession, hours: int = 24, organisation_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    stmt = (
        select(
            func.date_trunc('hour', Telemetry.ts).label('bucket'),
            func.avg(Telemetry.fill_level).label('avg_fill'),
        )
        .select_from(Telemetry)
        .join(Bin, Bin.bin_id == Telemetry.bin_id)
        .where(Telemetry.ts >= cutoff)
    )
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    stmt = stmt.group_by(func.date_trunc('hour', Telemetry.ts)).order_by(func.date_trunc('hour', Telemetry.ts))
    result = await session.execute(stmt)
    rows = result.all()
    return [{'ts': row.bucket.isoformat() if row.bucket else '', 'value': float(row.avg_fill or 0.0)} for row in rows]


async def get_class_distribution(session: AsyncSession, hours: int = 24, organisation_id: int | None = None) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    stmt = (
        select(Classification.predicted_class, func.count().label('count'))
        .select_from(Classification)
        .join(Bin, Bin.bin_id == Classification.bin_id)
        .where(Classification.ts >= cutoff)
    )
    if organisation_id is not None:
        stmt = stmt.where(Bin.organisation_id == organisation_id)
    stmt = stmt.group_by(Classification.predicted_class).order_by(func.count().desc())
    result = await session.execute(stmt)
    rows = result.all()
    return [{'label': row.predicted_class, 'count': int(row.count)} for row in rows]
