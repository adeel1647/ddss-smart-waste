from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Telemetry, Classification, Alert, RoutePlan


async def get_analytics_overview(session: AsyncSession) -> dict:
    today = datetime.now(timezone.utc) - timedelta(days=1)

    avg_fill_today = float(
        (await session.scalar(
            select(func.avg(Telemetry.fill_level)).where(Telemetry.ts >= today)
        )) or 0.0
    )

    max_fill_today = float(
        (await session.scalar(
            select(func.max(Telemetry.fill_level)).where(Telemetry.ts >= today)
        )) or 0.0
    )

    critical_alerts_today = int(
        (await session.scalar(
            select(func.count()).select_from(Alert).where(
                Alert.created_at >= today,
                Alert.severity == "critical",
            )
        )) or 0
    )

    open_alerts_total = int(
        (await session.scalar(
            select(func.count()).select_from(Alert).where(Alert.status == "open")
        )) or 0
    )

    latest_route_distance_km = float(
        (await session.scalar(
            select(RoutePlan.total_distance_km).order_by(RoutePlan.ts.desc()).limit(1)
        )) or 0.0
    )

    top_waste_class_today = await session.scalar(
        select(Classification.predicted_class)
        .where(Classification.ts >= today)
        .group_by(Classification.predicted_class)
        .order_by(func.count().desc())
        .limit(1)
    )

    return {
        "avg_fill_today": round(avg_fill_today, 2),
        "max_fill_today": round(max_fill_today, 2),
        "critical_alerts_today": critical_alerts_today,
        "open_alerts_total": open_alerts_total,
        "latest_route_distance_km": round(latest_route_distance_km, 2),
        "top_waste_class_today": top_waste_class_today,
    }


async def get_fill_trend(session: AsyncSession, hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await session.execute(
        select(
            func.date_trunc("hour", Telemetry.ts).label("bucket"),
            func.avg(Telemetry.fill_level).label("avg_fill"),
        )
        .where(Telemetry.ts >= cutoff)
        .group_by(func.date_trunc("hour", Telemetry.ts))
        .order_by(func.date_trunc("hour", Telemetry.ts))
    )

    rows = result.all()
    return [
        {
            "ts": row.bucket.isoformat() if row.bucket else "",
            "value": float(row.avg_fill or 0.0),
        }
        for row in rows
    ]


async def get_class_distribution(session: AsyncSession, hours: int = 24) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await session.execute(
        select(
            Classification.predicted_class,
            func.count().label("count"),
        )
        .where(Classification.ts >= cutoff)
        .group_by(Classification.predicted_class)
        .order_by(func.count().desc())
    )

    rows = result.all()
    return [{"label": row.predicted_class, "count": int(row.count)} for row in rows]