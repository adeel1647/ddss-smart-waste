from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_session
from app.repositories.bins import list_bins
from app.repositories.classifications import get_latest_classifications_for_bins
from app.repositories.decisions import create_run_with_items, list_items_for_run
from app.repositories.telemetry import get_latest_telemetry_for_bins, get_recent_fill_lags_for_bins
from app.schemas.ddss import DDSSBinDecision, DDSSRunRequest, DDSSRunResponse
from app.services.alerts import generate_alerts_for_run
from app.services.forecaster import ForecastInput, ForecastService
from app.services.priority import PriorityInputs, compute_priority_score, evaluate_service_window

router = APIRouter(tags=['ddss'])
log = logging.getLogger('app.ddss')


@router.post('/ddss/run', response_model=DDSSRunResponse)
async def run_ddss(
    req: DDSSRunRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        f'ddss-run:{client_ip}',
        limit=settings.ddss_run_rate_limit_per_minute,
        window_seconds=60,
        detail='Too many DDSS runs. Please wait a moment and try again.',
    )

    bins = await list_bins(session, postcode=req.postcode, sector=req.sector, active=True, limit=req.limit)
    if not bins:
        raise HTTPException(status_code=404, detail='No active bins found')

    bin_ids = [item.bin_id for item in bins]
    latest_tel = await get_latest_telemetry_for_bins(session, bin_ids)
    latest_cls = await get_latest_classifications_for_bins(session, bin_ids)
    lag_map = await get_recent_fill_lags_for_bins(session, bin_ids, take=3)

    forecaster: ForecastService = request.app.state.forecast_service
    now = datetime.now(timezone.utc)
    items_payload: list[dict] = []
    meta_by_bin: dict[str, dict] = {}

    for item in bins:
        telemetry = latest_tel.get(item.bin_id)
        if telemetry is None:
            continue

        interval_days = int(getattr(item, 'collection_interval_days', settings.default_collection_interval_days) or settings.default_collection_interval_days)
        lags = lag_map.get(item.bin_id) or [float(telemetry.fill_level)] * 3
        while len(lags) < 3:
            lags.insert(0, float(telemetry.fill_level))

        growth_rate = max(0.0, float(lags[-1] - lags[0]) / max(1, len(lags) - 1)) if len(lags) > 1 else 0.0
        forecast_input = ForecastInput(
            bin_id=item.bin_id,
            fill_level=float(telemetry.fill_level),
            hour_of_day=now.hour,
            day=now.weekday(),
            weekend=1 if now.weekday() >= 5 else 0,
            growth_rate=growth_rate,
            lags=lags,
            rolling_mean_3=sum(lags) / len(lags),
        )
        predicted_fill = float(forecaster.predict_6h(forecast_input))

        classification = latest_cls.get(item.bin_id)
        if classification is None:
            predicted_class = 'unknown'
            confidence_for_priority = 0.4
            confidence_stored = 0.0
        else:
            predicted_class = classification.predicted_class
            confidence_for_priority = float(classification.confidence)
            confidence_stored = float(classification.confidence)

        service = evaluate_service_window(float(telemetry.last_collection_hours), interval_days)
        uncertainty = float(max(0.0, min(1.0, 1.0 - confidence_for_priority)))
        priority = compute_priority_score(
            PriorityInputs(
                predicted_fill_6h=predicted_fill,
                last_collection_hours=float(telemetry.last_collection_hours),
                confidence=confidence_for_priority,
                collection_interval_days=interval_days,
            )
        )

        alerts: list[str] = []
        if predicted_fill >= settings.critical_fill_threshold:
            alerts.append('CRITICAL_FILL_PREDICTED')
        if service.status in {'critical_overdue', 'overdue'}:
            alerts.append('OVERDUE_COLLECTION')
        elif service.status == 'due_soon':
            alerts.append('COLLECTION_DUE_SOON')
        if classification is not None and float(classification.confidence) < settings.low_confidence_threshold:
            alerts.append('LOW_CLASSIFICATION_CONFIDENCE')

        items_payload.append(
            {
                'bin_id': item.bin_id,
                'predicted_class': predicted_class,
                'confidence': confidence_stored,
                'uncertainty': uncertainty,
                'current_fill': float(telemetry.fill_level),
                'predicted_fill_6h': predicted_fill,
                'last_collection_hours': float(telemetry.last_collection_hours),
                'priority_score': priority,
                'alerts': alerts,
            }
        )
        meta_by_bin[item.bin_id] = {
            'postcode': req.postcode,
            'sector': req.sector,
            'collection_interval_days': interval_days,
            'collection_weekday': getattr(item, 'collection_weekday', None),
            'service_status': service.status,
            'service_due_ratio': service.due_ratio,
            'scheduled_service_hours': service.scheduled_hours,
            'remaining_hours_to_due': service.remaining_hours,
        }

    if not items_payload:
        raise HTTPException(status_code=400, detail='No bins with telemetry available for DDSS processing')

    items_payload.sort(key=lambda x: x['priority_score'], reverse=True)
    items_payload = items_payload[: req.limit]

    run, _ = await create_run_with_items(session, postcode_filter=req.postcode, items=items_payload)
    await generate_alerts_for_run(session, run.id, commit=False)
    await session.commit()

    items = await list_items_for_run(session, run.id)
    ranked = [
        DDSSBinDecision(
            bin_id=decision.bin_id,
            predicted_class=decision.predicted_class,
            confidence=float(decision.confidence),
            uncertainty=float(decision.uncertainty),
            current_fill=float(decision.current_fill),
            predicted_fill_6h=float(decision.predicted_fill_6h),
            last_collection_hours=float(decision.last_collection_hours),
            priority_score=float(decision.priority_score),
            alerts=json.loads(decision.alerts_json),
            meta=meta_by_bin.get(decision.bin_id, {'postcode': req.postcode, 'sector': req.sector}),
        )
        for decision in items
    ]

    log.info('DDSS run completed', extra={'path': '/ddss/run', 'status_code': 200})
    return DDSSRunResponse(
        run_id=run.id,
        ts=run.ts,
        postcode_filter=run.postcode_filter,
        ranked_bins=ranked,
    )
