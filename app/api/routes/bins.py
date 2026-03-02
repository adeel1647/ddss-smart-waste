from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.common import BinCreate, BinOut
from app.repositories.bins import create_bin, get_bin, list_bins

router = APIRouter(tags=["bins"])

@router.post("/bins", response_model=BinOut)
async def create(req: BinCreate, session: AsyncSession = Depends(get_session)):
    b = await create_bin(session, req.postcode, req.lat, req.lon, req.active)
    return BinOut(
        bin_id=b.bin_id,
        postcode=getattr(b, "postcode", None),
        lat=b.lat,
        lon=b.lon,
        active=b.active,
        created_at=b.created_at,
    )

@router.get("/bins", response_model=list[BinOut])
async def list_all(
    postcode: str | None = None,
    active: bool | None = True,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
):
    bins = await list_bins(session, postcode=postcode, active=active, limit=limit)
    return [
        BinOut(
            bin_id=b.bin_id,
            postcode=getattr(b, "postcode", None),
            lat=b.lat,
            lon=b.lon,
            active=b.active,
            created_at=b.created_at,
        )
        for b in bins
    ]

@router.get("/bins/{bin_id}", response_model=BinOut)
async def get_one(bin_id: str, session: AsyncSession = Depends(get_session)):
    b = await get_bin(session, bin_id)
    if not b:
        raise HTTPException(status_code=404, detail="bin not found.")
    return BinOut(bin_id=b.bin_id, postcode=b.postcode, lat=b.lat, lon=b.lon, active=b.active, created_at=b.created_at)
