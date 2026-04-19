from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_org_permission
from app.db.models import User
from app.db.session import get_session
from app.repositories.bins import get_bin
from app.repositories.telemetry import add_telemetry, latest_telemetry
from app.schemas.common import TelemetryCreate, TelemetryOut

router = APIRouter(tags=['telemetry'])


@router.post('/bins/{bin_id}/telemetry', response_model=TelemetryOut)
async def ingest(
    bin_id: str,
    req: TelemetryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = await get_bin(session, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail='Bin not found')

    await require_org_permission(session, user, record.organisation_id, 'telemetry:write')

    telemetry = await add_telemetry(session, bin_id, req.fill_level, req.last_collection_hours, req.ts)
    return TelemetryOut(
        id=telemetry.id,
        bin_id=telemetry.bin_id,
        ts=telemetry.ts,
        fill_level=telemetry.fill_level,
        last_collection_hours=telemetry.last_collection_hours,
    )


@router.get('/bins/{bin_id}/telemetry/latest', response_model=TelemetryOut)
async def latest(
    bin_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = await get_bin(session, bin_id)
    if not record:
        raise HTTPException(status_code=404, detail='Bin not found')

    await require_org_permission(session, user, record.organisation_id, 'telemetry:read')

    telemetry = await latest_telemetry(session, bin_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail='No telemetry for this bin')

    return TelemetryOut(
        id=telemetry.id,
        bin_id=telemetry.bin_id,
        ts=telemetry.ts,
        fill_level=telemetry.fill_level,
        last_collection_hours=telemetry.last_collection_hours,
    )