from __future__ import annotations

import base64
from io import BytesIO
from PIL import Image

def load_image_from_bytes(data: bytes, image_size: int) -> Image.Image:
    img = Image.open(BytesIO(data)).convert("RGB")
    return img.resize((image_size, image_size))

def load_image_from_base64(b64: str, image_size: int) -> Image.Image:
    raw = base64.b64decode(b64)
    return load_image_from_bytes(raw, image_size)
