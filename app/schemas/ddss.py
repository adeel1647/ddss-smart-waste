from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DDSSRunRequest(BaseModel):
    postcode: str | None = None
    sector: str | None = None
    limit: int = Field(default=200, ge=1, le=5000)

    @field_validator('postcode', 'sector')
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DDSSBinDecision(BaseModel):
    bin_id: str
    predicted_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    current_fill: float = Field(ge=0.0, le=100.0)
    predicted_fill_6h: float = Field(ge=0.0, le=100.0)
    last_collection_hours: float = Field(ge=0.0)
    priority_score: float
    alerts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class DDSSRunResponse(BaseModel):
    run_id: int
    ts: datetime
    postcode_filter: str | None = None
    ranked_bins: list[DDSSBinDecision]
