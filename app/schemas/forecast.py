from pydantic import BaseModel, Field
from typing import List, Optional

class ForecastRequest(BaseModel):
    bin_id: str
    fill_level: float = Field(ge=0.0, le=100.0)
    hour_of_day: int = Field(ge=0, le=23)
    day: int = Field(ge=0, le=6)
    weekend: int = Field(ge=0, le=1)
    growth_rate: float
    lags: List[float] = Field(default_factory=list)
    rolling_mean_3: Optional[float] = None

class ForecastResponse(BaseModel):
    bin_id: str
    predicted_fill_6h: float = Field(ge=0.0, le=100.0)
    model: str
