from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class PriorityInputs:
    predicted_fill_6h: float
    last_collection_hours: float
    confidence: float
    collection_interval_days: int = 7


@dataclass
class ServiceWindowStatus:
    status: str
    due_ratio: float
    scheduled_hours: float
    remaining_hours: float


def evaluate_service_window(last_collection_hours: float, collection_interval_days: int) -> ServiceWindowStatus:
    scheduled_hours = max(24.0, float(collection_interval_days) * 24.0)
    due_ratio = last_collection_hours / scheduled_hours if scheduled_hours > 0 else 0.0
    remaining_hours = scheduled_hours - last_collection_hours

    if due_ratio >= settings.collection_critical_ratio:
        status = 'critical_overdue'
    elif due_ratio >= settings.collection_overdue_ratio:
        status = 'overdue'
    elif due_ratio >= settings.collection_due_soon_ratio:
        status = 'due_soon'
    else:
        status = 'on_track'

    return ServiceWindowStatus(
        status=status,
        due_ratio=round(due_ratio, 4),
        scheduled_hours=scheduled_hours,
        remaining_hours=round(remaining_hours, 2),
    )


def compute_priority_score(inputs: PriorityInputs) -> float:
    """
    Returns a normalized priority score in the range 0-100.

    The collection component is now based on the configured service interval
    for the bin, not a fixed 48-hour assumption.
    """

    fill_score = max(0.0, min(1.0, inputs.predicted_fill_6h / 100.0))

    service = evaluate_service_window(
        last_collection_hours=inputs.last_collection_hours,
        collection_interval_days=inputs.collection_interval_days,
    )
    overdue_score = max(0.0, min(1.0, service.due_ratio))
    uncertainty_score = max(0.0, min(1.0, 1.0 - inputs.confidence))

    score_0_1 = (
        0.55 * fill_score
        + 0.30 * overdue_score
        + 0.15 * uncertainty_score
    )
    return round(score_0_1 * 100.0, 2)
