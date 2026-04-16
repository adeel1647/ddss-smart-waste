from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.geo import AddressResolveIn, AddressResolveOut, AddressSearchResponse, AddressSuggestionOut
from app.services.geocoding import GeocodingError, GeocodingService

router = APIRouter(prefix='/geo', tags=['geo'])


@router.get('/search', response_model=AddressSearchResponse)
async def search_addresses(
    q: str = Query(min_length=2, description='Postcode or address search text'),
    limit: int = Query(default=12, ge=1, le=25),
):
    try:
        items = await GeocodingService.search(q, limit=limit)
    except GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AddressSearchResponse(
        query=q,
        items=[AddressSuggestionOut(**item.as_dict()) for item in items],
    )


@router.get('/postcode/{postcode}', response_model=AddressSearchResponse)
async def search_by_postcode(
    postcode: str,
    limit: int = Query(default=25, ge=1, le=25),
):
    try:
        items = await GeocodingService.search(postcode, limit=limit)
    except GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AddressSearchResponse(
        query=postcode,
        items=[AddressSuggestionOut(**item.as_dict()) for item in items],
    )


@router.post('/resolve', response_model=AddressResolveOut)
async def resolve_address(payload: AddressResolveIn):
    try:
        resolved = await GeocodingService.resolve(**payload.model_dump())
    except GeocodingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AddressResolveOut(**resolved.as_dict())
