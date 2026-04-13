from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from io import BytesIO
import base64

import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.model_store import ModelStore


@dataclass
class Prediction:
    label: str
    confidence: float


@dataclass
class ExplainabilityResult:
    overlay_image_base64: str
    heatmap_image_base64: str
    explanation: str
    last_conv_layer: str


class ClassifierService:
    def __init__(self, class_names: List[str]):
        self.class_names = class_names
        self.last_conv_layer_name = "conv5_block16_concat"

    @staticmethod
    def load(model_path: str):
        import tensorflow as tf
        return tf.keras.models.load_model(model_path, compile=False)

    @staticmethod
    def preprocess(img: Image.Image) -> np.ndarray:
        arr = np.asarray(img).astype("float32") / 255.0
        return np.expand_dims(arr, axis=0)

    @staticmethod
    def _encode_pil_to_base64(img: Image.Image) -> str:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

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

    def predict_with_explainability(
        self, img: Image.Image, top_k: int | None = None
    ) -> Tuple[Prediction, List[Prediction], ExplainabilityResult]:
        import tensorflow as tf
        import cv2

        model = ModelStore.get_classifier()
        if model is None:
            raise RuntimeError("Classifier model not loaded.")

        x = self.preprocess(img)
        probs = np.asarray(model.predict(x, verbose=0)[0], dtype=float)

        k = top_k or settings.top_k
        idx = probs.argsort()[-k:][::-1].tolist()
        top = [Prediction(self.class_names[i], float(probs[i])) for i in idx]
        best = top[0]
        pred_index = int(idx[0])

        last_conv_layer_name = self.last_conv_layer_name

        grad_model = tf.keras.models.Model(
            inputs=model.inputs,
            outputs=[
                model.get_layer(last_conv_layer_name).output,
                model.output,
            ],
        )

        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model([x], training=False)
            class_channel = predictions[:, pred_index]

        grads = tape.gradient(class_channel, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        heatmap = tf.maximum(heatmap, 0)
        max_val = tf.reduce_max(heatmap)
        if float(max_val) > 0:
            heatmap = heatmap / max_val

        heatmap = heatmap.numpy()

        # Original image for display
        original = img.convert("RGB")
        original_np = np.array(original)

        # Resize heatmap to original image size
        heatmap_resized = cv2.resize(heatmap, (original_np.shape[1], original_np.shape[0]))
        heatmap_uint8 = np.uint8(255 * heatmap_resized)

        # Colored heatmap
        heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

        # Overlay
        overlay = cv2.addWeighted(original_np, 0.6, heatmap_color, 0.4, 0)

        heatmap_img = Image.fromarray(heatmap_color)
        overlay_img = Image.fromarray(overlay)

        explanation = (
            f"The model classified this image as '{best.label}' with "
            f"{best.confidence:.1%} confidence. The highlighted regions show "
            "the parts of the image that most influenced the prediction."
        )

        explainability = ExplainabilityResult(
            overlay_image_base64=self._encode_pil_to_base64(overlay_img),
            heatmap_image_base64=self._encode_pil_to_base64(heatmap_img),
            explanation=explanation,
            last_conv_layer=last_conv_layer_name,
        )

        return best, top, explainability