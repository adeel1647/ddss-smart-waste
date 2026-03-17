from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    id: int
    bin_id: str
    decision_run_id: Optional[int] = None
    alert_type: str
    severity: str
    message: str
    status: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    resolved_at: Optional[datetime] = None


class AlertListResponse(BaseModel):
    items: list[AlertOut]


class AlertSummaryOut(BaseModel):
    open_total: int
    critical_total: int
    warning_total: int
    info_total: int
    acknowledged_total: int
    resolved_total: int


class AlertUpdateIn(BaseModel):
    status: str  # acknowledged / resolved