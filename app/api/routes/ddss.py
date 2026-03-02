from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException
from datetime import datetime

from app.core.config import settings
from app.schemas.ddss import IoTData, ProcessBinResponse
from app.utils.images import load_image_from_bytes
from app.services.classifier import ClassifierService
from app.services.forecaster import ForecastService, ForecastInput
from app.services.priority import PriorityInputs, compute_priority_score

router = APIRouter(tags=["ddss"])

@router.post("/ddss/process-bin", response_model=ProcessBinResponse)
async def process_bin(
    bin_id: str,
    fill_level: float,
    last_collection_hours: float,
    postcode: str | None = None,
    growth_rate: float = 1.0,
    file: UploadFile | None = File(default=None),
):
    # Validate
    if not (0.0 <= fill_level <= 100.0):
        raise HTTPException(status_code=400, detail="fill_level must be 0-100.")
    if last_collection_hours < 0:
        raise HTTPException(status_code=400, detail="last_collection_hours must be >= 0.")

    classifier = request.app.state.classifier_service
    forecaster = request.app.state.forecast_service

    # If no image provided, treat confidence low and class unknown
    predicted_class = "unknown"
    confidence = 0.0

    if file is not None:
        if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
            raise HTTPException(status_code=400, detail="Only JPEG/PNG images are supported.")
        data = await file.read()
        img = load_image_from_bytes(data, settings.image_size)
        best, _ = classifier.predict(img)
        predicted_class = best.label
        confidence = best.confidence

    now = datetime.utcnow()
    weekend = 1 if now.weekday() >= 5 else 0

    # Minimal history support: client can improve this by sending lags; server keeps it simple
    fi = ForecastInput(
        bin_id=bin_id,
        fill_level=fill_level,
        hour_of_day=now.hour,
        day=now.weekday(),
        weekend=weekend,
        growth_rate=growth_rate,
        lags=[fill_level, fill_level, fill_level],
        rolling_mean_3=fill_level,
    )
    predicted_fill = forecaster.predict_6h(fi)

    priority = compute_priority_score(PriorityInputs(
        predicted_fill_6h=predicted_fill,
        last_collection_hours=last_collection_hours,
        confidence=confidence if confidence > 0 else 0.4,  # default uncertainty if no image
    ))
    uncertainty = 1.0 - (confidence if confidence > 0 else 0.4)

    alerts = []
    if predicted_fill >= 90:
        alerts.append("CRITICAL_FILL_PREDICTED")
    if last_collection_hours >= 36:
        alerts.append("OVERDUE_COLLECTION")
    if confidence > 0 and confidence < 0.6:
        alerts.append("LOW_CLASSIFICATION_CONFIDENCE")

    return ProcessBinResponse(
        bin_id=bin_id,
        predicted_class=predicted_class,
        confidence=confidence if confidence > 0 else 0.0,
        uncertainty=float(max(0.0, min(1.0, uncertainty))),
        current_fill=fill_level,
        predicted_fill_6h=predicted_fill,
        last_collection_hours=last_collection_hours,
        priority_score=priority,
        alerts=alerts,
        meta={"postcode": postcode},
    )
