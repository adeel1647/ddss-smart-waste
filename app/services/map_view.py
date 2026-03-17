from __future__ import annotations

import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Bin, Telemetry, Classification, DecisionRun, DecisionItem, RoutePlan, RouteTrip


def compute_status(active: bool, predicted_fill_6h: float | None, alert_types: list[str]) -> str:
    if not active:
        return "inactive"
    if "CRITICAL_FILL_PREDICTED" in alert_types or (predicted_fill_6h is not None and predicted_fill_6h >= 90):
        return "critical"
    if predicted_fill_6h is not None and predicted_fill_6h >= 70:
        return "warning"
    return "healthy"


async def get_map_bins(session: AsyncSession) -> list[dict]:
    latest_run_id = await session.scalar(select(func.max(DecisionRun.id)))
    latest_plan_id = await session.scalar(select(func.max(RoutePlan.id)))

    latest_tel_subq = (
        select(Telemetry.bin_id, func.max(Telemetry.ts).label("max_ts"))
        .group_by(Telemetry.bin_id)
        .subquery()
    )

    latest_cls_subq = (
        select(Classification.bin_id, func.max(Classification.ts).label("max_ts"))
        .group_by(Classification.bin_id)
        .subquery()
    )

    telemetry_rows = await session.execute(
        select(Telemetry)
        .join(
            latest_tel_subq,
            (Telemetry.bin_id == latest_tel_subq.c.bin_id) & (Telemetry.ts == latest_tel_subq.c.max_ts),
        )
    )
    latest_tel = {row.bin_id: row for row in telemetry_rows.scalars().all()}

    cls_rows = await session.execute(
        select(Classification)
        .join(
            latest_cls_subq,
            (Classification.bin_id == latest_cls_subq.c.bin_id) & (Classification.ts == latest_cls_subq.c.max_ts),
        )
    )
    latest_cls = {row.bin_id: row for row in cls_rows.scalars().all()}

    latest_items = {}
    if latest_run_id:
        items_result = await session.execute(
            select(DecisionItem).where(DecisionItem.run_id == latest_run_id)
        )
        latest_items = {row.bin_id: row for row in items_result.scalars().all()}

    routed_bins: set[str] = set()
    if latest_plan_id:
        trips_result = await session.execute(
            select(RouteTrip).where(RouteTrip.plan_id == latest_plan_id)
        )
        trips = trips_result.scalars().all()
        for trip in trips:
            try:
                stops = json.loads(trip.stops_json or "[]")
            except Exception:
                stops = []
            for stop in stops:
                if isinstance(stop, dict) and stop.get("bin_id"):
                    routed_bins.add(stop["bin_id"])
                elif isinstance(stop, str):
                    routed_bins.add(stop)

    bins_result = await session.execute(select(Bin))
    bins = bins_result.scalars().all()

    items: list[dict] = []

    for b in bins:
        tel = latest_tel.get(b.bin_id)
        cls = latest_cls.get(b.bin_id)
        item = latest_items.get(b.bin_id)

        try:
            alerts = json.loads(item.alerts_json) if item else []
        except Exception:
            alerts = []

        status = compute_status(
            b.active,
            item.predicted_fill_6h if item else None,
            alerts,
        )

        items.append(
            {
                "bin_id": b.bin_id,
                "postcode": b.postcode,
                "lat": b.lat,
                "lon": b.lon,
                "active": b.active,
                "current_fill": tel.fill_level if tel else None,
                "predicted_fill_6h": item.predicted_fill_6h if item else None,
                "last_collection_hours": tel.last_collection_hours if tel else None,
                "predicted_class": cls.predicted_class if cls else None,
                "confidence": cls.confidence if cls else None,
                "priority_score": item.priority_score if item else None,
                "alerts": alerts,
                "status": status,
                "in_latest_route": b.bin_id in routed_bins,
            }
        )

    return items