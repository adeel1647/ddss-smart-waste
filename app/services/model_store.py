from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional


class ModelStore:
    _lock = threading.Lock()
    _classifier: Optional[Any] = None
    _forecaster: Optional[Any] = None
    _classifier_meta: dict[str, Any] = {}
    _forecaster_meta: dict[str, Any] = {}

    @classmethod
    def get_classifier(cls) -> Optional[Any]:
        return cls._classifier

    @classmethod
    def set_classifier(cls, model: Any, *, path: str | None = None, version: str | None = None) -> None:
        with cls._lock:
            cls._classifier = model
            cls._classifier_meta = {
                'loaded': model is not None,
                'path': path,
                'version': version or (Path(path).name if path else None),
                'model_type': type(model).__name__ if model is not None else None,
            }

    @classmethod
    def get_forecaster(cls) -> Optional[Any]:
        return cls._forecaster

    @classmethod
    def set_forecaster(cls, model: Any, *, path: str | None = None, version: str | None = None) -> None:
        with cls._lock:
            cls._forecaster = model
            cls._forecaster_meta = {
                'loaded': model is not None,
                'path': path,
                'version': version or (Path(path).name if path else None),
                'model_type': type(model).__name__ if model is not None else None,
            }

    @classmethod
    def get_health(cls) -> dict[str, dict[str, Any]]:
        return {
            'classifier': {
                'loaded': cls._classifier is not None,
                **cls._classifier_meta,
            },
            'forecaster': {
                'loaded': cls._forecaster is not None,
                **cls._forecaster_meta,
            },
        }
