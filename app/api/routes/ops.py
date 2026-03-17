from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.ops import OpsSummaryOut
from app.services.ops_summary import get_ops_summary

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/summary", response_model=OpsSummaryOut)
async def ops_summary(
    session: AsyncSession = Depends(get_session),
):
    return await get_ops_summary(session)