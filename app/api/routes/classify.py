from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.classify import ClassifyResponse, TopKItem
from app.core.config import settings
from app.utils.images import load_image_from_bytes
from app.services.classifier import ClassifierService
from app.db.session import get_session
from app.repositories.bins import get_bin
from app.repositories.classifications import add_classification

router = APIRouter(tags=["classifier"])

@router.post("/classify", response_model=ClassifyResponse)
async def classify_image(
    request: Request,
    bin_id: str | None = None,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    if file.content_type not in {"image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG images are supported.")

    data = await file.read()
    img = load_image_from_bytes(data, settings.image_size)

    svc: ClassifierService = request.app.state.classifier_service
    best, top = svc.predict(img, top_k=settings.top_k)

    if bin_id is not None:
        b = await get_bin(session, bin_id)
        if not b:
            raise HTTPException(status_code=404, detail="bin_id not found (register the bin first).")
        await add_classification(session, bin_id=bin_id, predicted_class=best.label, confidence=best.confidence)

    return ClassifyResponse(
        predicted_class=best.label,
        confidence=best.confidence,
        top_k=[TopKItem(label=p.label, confidence=p.confidence) for p in top],
    )