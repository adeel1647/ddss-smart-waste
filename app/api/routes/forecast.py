from __future__ import annotations

from fastapi import APIRouter
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.forecaster import ForecastService, ForecastInput

router = APIRouter(tags=["forecast"])

@router.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    svc: ForecastService = request.app.state.forecast_service
    fi = ForecastInput(
        bin_id=req.bin_id,
        fill_level=req.fill_level,
        hour_of_day=req.hour_of_day,
        day=req.day,
        weekend=req.weekend,
        growth_rate=req.growth_rate,
        lags=req.lags,
        rolling_mean_3=req.rolling_mean_3,
    )
    pred = svc.predict_6h(fi)
    return ForecastResponse(bin_id=req.bin_id, predicted_fill_6h=pred, model="random_forest")
