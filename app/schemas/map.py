from __future__ import annotations

from pydantic import BaseModel


class MapBinOut(BaseModel):
    bin_id: str
    postcode: str | None = None
    lat: float
    lon: float
    active: bool

    current_fill: float | None = None
    predicted_fill_6h: float | None = None
    last_collection_hours: float | None = None

    predicted_class: str | None = None
    confidence: float | None = None

    priority_score: float | None = None
    alerts: list[str] = []
    status: str
    in_latest_route: bool = False


class MapBinsResponse(BaseModel):
    items: list[MapBinOut]