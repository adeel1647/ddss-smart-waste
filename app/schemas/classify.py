from pydantic import BaseModel, Field
from typing import List

class TopKItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)

class ClassifyResponse(BaseModel):
    predicted_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_k: List[TopKItem]
