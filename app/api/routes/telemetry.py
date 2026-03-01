from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.common import TelemetryCreate, TelemetryOut
from app.repositories.bins import get_bin
from app.repositories.telemetry import add_telemetry, latest_telemetry

router = APIRouter(tags=["telemetry"])

@router.post("/bins/{bin_id}/telemetry", response_model=TelemetryOut)
async def ingest(bin_id: str, req: TelemetryCreate, session: AsyncSession = Depends(get_session)):
    b = await get_bin(session, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="bin not found.")
    t = await add_telemetry(session, bin_id, req.fill_level, req.last_collection_hours, req.ts)
    return TelemetryOut(id=t.id, bin_id=t.bin_id, ts=t.ts, fill_level=t.fill_level, last_collection_hours=t.last_collection_hours)

@router.get("/bins/{bin_id}/telemetry/latest", response_model=TelemetryOut)
async def latest(bin_id: str, session: AsyncSession = Depends(get_session)):
    t = await latest_telemetry(session, bin_id)
    if not t:
        raise HTTPException(status_code=404, detail="no telemetry for this bin.")
    return TelemetryOut(id=t.id, bin_id=t.bin_id, ts=t.ts, fill_level=t.fill_level, last_collection_hours=t.last_collection_hours)
