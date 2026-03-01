from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from app.services.model_store import ModelStore

DEFAULT_FEATURES = [
    "fill_level", "hour_of_day", "day", "weekend", "growth_rate",
    "lag_1", "lag_2", "lag_3", "rolling_mean_3"
]

@dataclass
class ForecastInput:
    bin_id: str
    fill_level: float
    hour_of_day: int
    day: int
    weekend: int
    growth_rate: float
    lags: List[float]
    rolling_mean_3: Optional[float] = None

class ForecastService:
    @staticmethod
    def load(model_path: str):
        import joblib
        return joblib.load(model_path)

    @staticmethod
    def _feature_names(model) -> List[str]:
        names = getattr(model, "feature_names_in_", None)
        return list(names) if names is not None else DEFAULT_FEATURES

    def predict_6h(self, fi: ForecastInput) -> float:
        model = ModelStore.get_forecaster()
        if model is None:
            raise RuntimeError("Forecast model not loaded.")
        names = self._feature_names(model)

        lags = (fi.lags or [])[-3:]
        while len(lags) < 3:
            lags.insert(0, fi.fill_level)
        rolling = fi.rolling_mean_3 if fi.rolling_mean_3 is not None else float(np.mean(lags))

        row = {
            "fill_level": fi.fill_level,
            "hour_of_day": fi.hour_of_day,
            "day": fi.day,
            "weekend": fi.weekend,
            "growth_rate": fi.growth_rate,
            "lag_1": lags[-1],
            "lag_2": lags[-2],
            "lag_3": lags[-3],
            "rolling_mean_3": rolling,
        }
        X = pd.DataFrame([row])[names]
        pred = float(model.predict(X)[0])
        return float(max(0.0, min(100.0, pred)))
