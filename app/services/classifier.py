from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.model_store import ModelStore

@dataclass
class Prediction:
    label: str
    confidence: float

class ClassifierService:
    def __init__(self, class_names: List[str]):
        self.class_names = class_names

    @staticmethod
    def load(model_path: str):
        import tensorflow as tf
        return tf.keras.models.load_model(model_path, compile=False)

    @staticmethod
    def preprocess(img: Image.Image) -> np.ndarray:
        arr = np.asarray(img).astype("float32") / 255.0
        return np.expand_dims(arr, axis=0)

    def predict(self, img: Image.Image, top_k: int | None = None) -> Tuple[Prediction, List[Prediction]]:
        model = ModelStore.get_classifier()
        if model is None:
            raise RuntimeError("Classifier model not loaded.")
        x = self.preprocess(img)
        probs = np.asarray(model.predict(x, verbose=0)[0], dtype=float)
        k = top_k or settings.top_k
        idx = probs.argsort()[-k:][::-1].tolist()
        top = [Prediction(self.class_names[i], float(probs[i])) for i in idx]
        return top[0], top
