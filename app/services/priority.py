from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriorityInputs:
    predicted_fill_6h: float
    last_collection_hours: float
    confidence: float


def compute_priority_score(inputs: PriorityInputs) -> float:
    """
    Returns a NORMALIZED priority score in the range 0-100.

    Interpretation:
    - 0-39   = low priority
    - 40-59  = moderate
    - 60-79  = high
    - 80-100 = urgent
    """

    # 1) Fill risk: 0-1
    fill_score = max(0.0, min(1.0, inputs.predicted_fill_6h / 100.0))

    # 2) Overdue score: normalize against 48h
    overdue_score = max(0.0, min(1.0, inputs.last_collection_hours / 48.0))

    # 3) Uncertainty score: lower confidence => higher uncertainty
    uncertainty_score = max(0.0, min(1.0, 1.0 - inputs.confidence))

    # Weighted sum
    score_0_1 = (
        0.55 * fill_score
        + 0.30 * overdue_score
        + 0.15 * uncertainty_score
    )

    # Convert to 0-100
    return round(score_0_1 * 100.0, 2)