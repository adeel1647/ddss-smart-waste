from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.ddss import DDSSBinDecision
from app.schemas.routing import Trip

class LatestDDSSResponse(BaseModel):
    run_id: int
    ts: datetime
    postcode_filter: Optional[str] = None
    ranked_bins: List[DDSSBinDecision]

class LatestRouteResponse(BaseModel):
    plan_id: int
    ts: datetime
    decision_run_id: int
    strategy: str
    total_distance_km: float
    trips: List[Trip]
