from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.repositories.bins import get_bins_by_ids
from app.repositories.decisions import latest_run, list_items_for_run
from app.schemas.ddss import DDSSBinDecision
from app.schemas.latest import LatestDDSSResponse
from app.services.priority import evaluate_service_window

router = APIRouter(tags=['ddss'])


@router.get('/ddss/latest', response_model=LatestDDSSResponse)
async def latest_ddss(
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail='No decision run found.')
    items = await list_items_for_run(session, run.id)
    bins_by_id = await get_bins_by_ids(session, [item.bin_id for item in items])
    return LatestDDSSResponse(
        run_id=run.id,
        ts=run.ts,
        postcode_filter=run.postcode_filter,
        ranked_bins=[
            DDSSBinDecision(
                bin_id=i.bin_id,
                predicted_class=i.predicted_class,
                confidence=float(i.confidence),
                uncertainty=float(i.uncertainty),
                current_fill=float(i.current_fill),
                predicted_fill_6h=float(i.predicted_fill_6h),
                last_collection_hours=float(i.last_collection_hours),
                priority_score=float(i.priority_score),
                alerts=json.loads(i.alerts_json or '[]'),
                meta=_meta_for_bin(i, bins_by_id.get(i.bin_id)),
            )
            for i in items
        ],
    )


def _meta_for_bin(item, bin_row):
    interval_days = int(getattr(bin_row, 'collection_interval_days', settings.default_collection_interval_days) or settings.default_collection_interval_days)
    service = evaluate_service_window(float(item.last_collection_hours), interval_days)
    return {
        'collection_interval_days': interval_days,
        'collection_weekday': getattr(bin_row, 'collection_weekday', None) if bin_row else None,
        'service_status': service.status,
        'service_due_ratio': service.due_ratio,
        'scheduled_service_hours': service.scheduled_hours,
        'remaining_hours_to_due': service.remaining_hours,
    }
