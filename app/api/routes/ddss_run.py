from __future__ import annotations

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.repositories.bins import list_bins
from app.repositories.telemetry import latest_telemetry, last_n_fill_levels
from app.repositories.classifications import latest_classification
from app.repositories.decisions import create_run, add_item, list_items_for_run
from app.schemas.ddss import DDSSRunRequest, DDSSRunResponse, DDSSBinDecision
from app.services.forecaster import ForecastService, ForecastInput
from app.services.priority import PriorityInputs, compute_priority_score

router = APIRouter(tags=["ddss"])

@router.post("/ddss/run", response_model=DDSSRunResponse)
async def run_ddss(req: DDSSRunRequest, session: AsyncSession = Depends(get_session)):
    bins = await list_bins(session, sector=req.sector, active=True, limit=req.limit)
    if not bins:
        raise HTTPException(status_code=404, detail="No active bins found (register bins first).")

    run = await create_run(session, sector_filter=req.sector)
    forecaster: ForecastService = router.app.state.forecast_service

    # Compute decisions and persist
    for b in bins:
        t = await latest_telemetry(session, b.bin_id)
        if t is None:
            continue

        lags = await last_n_fill_levels(session, b.bin_id, n=3)
        if not lags:
            lags = [t.fill_level, t.fill_level, t.fill_level]
        while len(lags) < 3:
            lags.insert(0, t.fill_level)

        now = datetime.utcnow()
        weekend = 1 if now.weekday() >= 5 else 0
        growth_rate = 1.0

        fi = ForecastInput(
            bin_id=b.bin_id,
            fill_level=float(t.fill_level),
            hour_of_day=now.hour,
            day=now.weekday(),
            weekend=weekend,
            growth_rate=growth_rate,
            lags=lags,
            rolling_mean_3=sum(lags) / len(lags),
        )
        predicted_fill = forecaster.predict_6h(fi)

        cls = await latest_classification(session, b.bin_id)
        if cls is None:
            predicted_class = "unknown"
            confidence_for_priority = 0.4
            confidence_stored = 0.0
        else:
            predicted_class = cls.predicted_class
            confidence_for_priority = float(cls.confidence)
            confidence_stored = float(cls.confidence)

        uncertainty = float(max(0.0, min(1.0, 1.0 - confidence_for_priority)))
        priority = compute_priority_score(PriorityInputs(
            predicted_fill_6h=predicted_fill,
            last_collection_hours=float(t.last_collection_hours),
            confidence=confidence_for_priority,
        ))

        alerts: list[str] = []
        if predicted_fill >= settings.critical_fill_threshold:
            alerts.append("CRITICAL_FILL_PREDICTED")
        if float(t.last_collection_hours) >= settings.overdue_hours_threshold:
            alerts.append("OVERDUE_COLLECTION")
        if cls is not None and float(cls.confidence) < settings.low_confidence_threshold:
            alerts.append("LOW_CLASSIFICATION_CONFIDENCE")

        await add_item(
            session=session,
            run_id=run.id,
            bin_id=b.bin_id,
            predicted_class=predicted_class,
            confidence=confidence_stored,
            uncertainty=uncertainty,
            current_fill=float(t.fill_level),
            predicted_fill_6h=predicted_fill,
            last_collection_hours=float(t.last_collection_hours),
            priority_score=priority,
            alerts=alerts,
        )

    items = await list_items_for_run(session, run.id)
    ranked = [
        DDSSBinDecision(
            bin_id=it.bin_id,
            predicted_class=it.predicted_class,
            confidence=float(it.confidence),
            uncertainty=float(it.uncertainty),
            current_fill=float(it.current_fill),
            predicted_fill_6h=float(it.predicted_fill_6h),
            last_collection_hours=float(it.last_collection_hours),
            priority_score=float(it.priority_score),
            alerts=json.loads(it.alerts_json),
            meta={"sector": req.sector},
        )
        for it in items
    ]

    return DDSSRunResponse(run_id=run.id, ts=run.ts, sector_filter=run.sector_filter, ranked_bins=ranked)
