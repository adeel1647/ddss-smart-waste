from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkOrderOut(BaseModel):
    id: int
    bin_id: str
    alert_id: int | None = None
    route_plan_id: int | None = None
    title: str
    description: str | None = None
    priority: str
    status: str
    assigned_to: str | None = None
    due_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class WorkOrderCreateFromAlerts(BaseModel):
    alert_ids: list[int] = Field(default_factory=list)
    assigned_to: str | None = Field(default=None, max_length=120)
    due_hours: int = Field(default=24, ge=1, le=240)


class WorkOrderCreateFromLatestRoute(BaseModel):
    assigned_to: str | None = Field(default=None, max_length=120)
    due_hours: int = Field(default=24, ge=1, le=240)
    top_n: int = Field(default=10, ge=1, le=500)


class WorkOrderUpdateIn(BaseModel):
    status: str | None = None
    assigned_to: str | None = Field(default=None, max_length=120)
    resolution_notes: str | None = None
