from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DDSSRunRequest(BaseModel):
    postcode: Optional[str] = None
    limit: int = Field(default=200, ge=1, le=5000)

class DDSSBinDecision(BaseModel):
    bin_id: str
    predicted_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    current_fill: float = Field(ge=0.0, le=100.0)
    predicted_fill_6h: float = Field(ge=0.0, le=100.0)
    last_collection_hours: float = Field(ge=0.0)
    priority_score: float
    alerts: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

class DDSSRunResponse(BaseModel):
    run_id: int
    ts: datetime
    postcode_filter: Optional[str] = None
    ranked_bins: List[DDSSBinDecision]
