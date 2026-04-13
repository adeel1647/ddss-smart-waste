from pydantic import BaseModel, Field
from typing import List, Optional


class TopKItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class ImageExplainabilityOut(BaseModel):
    overlay_image_base64: str
    heatmap_image_base64: str
    explanation: str
    last_conv_layer: str


class ClassifyResponse(BaseModel):
    predicted_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    top_k: List[TopKItem]
    stored: bool = False
    image_explainability: Optional[ImageExplainabilityOut] = None