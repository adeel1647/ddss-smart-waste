from __future__ import annotations
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class PriorityInputs:
    predicted_fill_6h: float
    last_collection_hours: float
    confidence: float

def compute_priority_score(inp: PriorityInputs) -> float:
    uncertainty = 1.0 - float(inp.confidence)
    return float(
        settings.w_fill * float(inp.predicted_fill_6h)
        + settings.w_last_collection * float(inp.last_collection_hours)
        + settings.w_uncertainty * float(uncertainty) * 100.0
    )
