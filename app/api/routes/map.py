from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.map import MapBinsResponse
from app.services.map_view import get_map_bins

router = APIRouter(prefix='/map', tags=['map'])


@router.get('/bins', response_model=MapBinsResponse)
async def map_bins(
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    items = await get_map_bins(session)
    return {'items': items}
