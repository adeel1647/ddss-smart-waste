from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskScoreOut(BaseModel):
    bin_id: str
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    current_fill: float
    predicted_fill_6h: float
    overflow_eta_hours: float | None = None
    overflow_risk_probability: float
    anomaly_score: float
    anomaly_flags: list[str] = Field(default_factory=list)
    contamination_risk_probability: float
    contamination_reasons: list[str] = Field(default_factory=list)
    recommended_action: str
    generated_at: datetime


class RiskListResponse(BaseModel):
    items: list[RiskScoreOut]


class ExplainabilityOut(BaseModel):
    bin_id: str
    generated_at: datetime
    summary: str
    recommendation: str
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)
    risk: RiskScoreOut


class AnomalyEventOut(BaseModel):
    bin_id: str
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    latest_fill: float
    expected_fill: float
    delta: float
    anomaly_score: float
    flags: list[str] = Field(default_factory=list)
    ts: datetime


class AnomalyListResponse(BaseModel):
    items: list[AnomalyEventOut]


class ContaminationCaseCreate(BaseModel):
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    bin_id: str
    source: Literal['manual', 'model', 'sensor', 'rule'] = 'manual'
    contamination_type: str = 'mixed_waste'
    severity: Literal['low', 'medium', 'high', 'critical'] = 'medium'
    probability: float | None = None
    status: Literal['open', 'investigating', 'resolved', 'dismissed'] = 'open'
    notes: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ContaminationCaseUpdate(BaseModel):
    severity: Literal['low', 'medium', 'high', 'critical'] | None = None
    probability: float | None = None
    status: Literal['open', 'investigating', 'resolved', 'dismissed'] | None = None
    notes: str | None = None
    evidence: dict[str, Any] | None = None


class ContaminationCaseOut(BaseModel):
    id: int
    organisation_id: int | None = None
    site_id: int | None = None
    zone_id: int | None = None
    bin_id: str
    source: str
    contamination_type: str
    severity: str
    probability: float | None = None
    status: str
    notes: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class ContaminationCaseListResponse(BaseModel):
    items: list[ContaminationCaseOut]


class ModelMetricSnapshotCreate(BaseModel):
    model_name: str
    model_version: str | None = None
    metric_name: str
    metric_value: float
    window_label: str | None = None
    sample_size: int | None = None
    status: Literal['ok', 'warning', 'critical'] = 'ok'
    meta: dict[str, Any] = Field(default_factory=dict)


class ModelMetricSnapshotOut(BaseModel):
    id: int
    model_name: str
    model_version: str | None = None
    metric_name: str
    metric_value: float
    window_label: str | None = None
    sample_size: int | None = None
    status: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MonitoringSummaryMetric(BaseModel):
    metric_name: str
    latest_value: float
    status: str
    sample_size: int | None = None
    model_version: str | None = None
    last_created_at: datetime


class MonitoringSummaryOut(BaseModel):
    model_name: str
    days: int
    metrics: list[MonitoringSummaryMetric] = Field(default_factory=list)
