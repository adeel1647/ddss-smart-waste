from __future__ import annotations
import threading
from typing import Optional, Any

class ModelStore:
    _lock = threading.Lock()
    _classifier: Optional[Any] = None
    _forecaster: Optional[Any] = None

    @classmethod
    def get_classifier(cls) -> Optional[Any]:
        return cls._classifier

    @classmethod
    def set_classifier(cls, model: Any) -> None:
        with cls._lock:
            cls._classifier = model

    @classmethod
    def get_forecaster(cls) -> Optional[Any]:
        return cls._forecaster

    @classmethod
    def set_forecaster(cls, model: Any) -> None:
        with cls._lock:
            cls._forecaster = model
