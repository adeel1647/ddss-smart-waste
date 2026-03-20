from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bin, Alert, DecisionRun, DecisionItem, RoutePlan, Telemetry


async def get_ops_summary(session: AsyncSession) -> dict:
    total_bins = await session.scalar(select(func.count()).select_from(Bin)) or 0
    active_bins = await session.scalar(
        select(func.count()).select_from(Bin).where(Bin.active.is_(True))
    ) or 0
    inactive_bins = total_bins - active_bins

    latest_run_id = await session.scalar(select(func.max(DecisionRun.id)))
    latest_plan_id = await session.scalar(select(func.max(RoutePlan.id)))

    critical_bins = 0
    warning_bins = 0
    healthy_bins = 0
    avg_predicted_fill_6h = 0.0

    if latest_run_id:
        result = await session.execute(
            select(
                func.avg(DecisionItem.predicted_fill_6h),
                func.sum(case((DecisionItem.predicted_fill_6h >= 90, 1), else_=0)),
                func.sum(
                    case(
                        (
                            (DecisionItem.predicted_fill_6h >= 70)
                            & (DecisionItem.predicted_fill_6h < 90),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(case((DecisionItem.predicted_fill_6h < 70, 1), else_=0)),
            ).where(DecisionItem.run_id == latest_run_id)
        )
        row = result.one()
        avg_predicted_fill_6h = float(row[0] or 0.0)
        critical_bins = int(row[1] or 0)
        warning_bins = int(row[2] or 0)
        healthy_bins = int(row[3] or 0)

    open_alerts = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == "open")
    ) or 0

    critical_alerts = await session.scalar(
        select(func.count()).select_from(Alert).where(
            Alert.status == "open",
            Alert.severity == "critical",
        )
    ) or 0

    latest_ts_subq = (
        select(Telemetry.bin_id, func.max(Telemetry.ts).label("max_ts"))
        .group_by(Telemetry.bin_id)
        .subquery()
    )

    latest_telemetry_q = (
        select(func.avg(Telemetry.fill_level))
        .join(
            latest_ts_subq,
            (Telemetry.bin_id == latest_ts_subq.c.bin_id)
            & (Telemetry.ts == latest_ts_subq.c.max_ts),
        )
    )
    avg_fill_level = float((await session.scalar(latest_telemetry_q)) or 0.0)

    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    stale_q = (
        select(func.count())
        .select_from(Telemetry)
        .join(
            latest_ts_subq,
            (Telemetry.bin_id == latest_ts_subq.c.bin_id)
            & (Telemetry.ts == latest_ts_subq.c.max_ts),
        )
        .where(Telemetry.ts < stale_cutoff)
    )
    stale_bins = int((await session.scalar(stale_q)) or 0)

    return {
        "total_bins": total_bins,
        "active_bins": active_bins,
        "inactive_bins": inactive_bins,
        "critical_bins": critical_bins,
        "warning_bins": warning_bins,
        "healthy_bins": healthy_bins,
        "stale_bins": stale_bins,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "latest_ddss_run_id": latest_run_id,
        "latest_route_plan_id": latest_plan_id,
        "avg_fill_level": round(avg_fill_level, 2),
        "avg_predicted_fill_6h": round(avg_predicted_fill_6h, 2),
    }