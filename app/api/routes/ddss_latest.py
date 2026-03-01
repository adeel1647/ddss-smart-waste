from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.decisions import latest_run, list_items_for_run
from app.schemas.latest import LatestDDSSResponse
from app.schemas.ddss import DDSSBinDecision

router = APIRouter(tags=["ddss"])

@router.get("/ddss/latest", response_model=LatestDDSSResponse)
async def latest_ddss(session: AsyncSession = Depends(get_session)):
    run = await latest_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail="No decision run found.")
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
            meta={"sector": run.sector_filter},
        )
        for it in items
    ]
    return LatestDDSSResponse(run_id=run.id, ts=run.ts, sector_filter=run.sector_filter, ranked_bins=ranked)
