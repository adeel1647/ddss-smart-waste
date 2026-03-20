from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_session
from app.repositories.bins import get_bin
from app.repositories.classifications import add_classification
from app.schemas.classify import ClassifyResponse, TopKItem
from app.services.classifier import ClassifierService
from app.utils.images import load_image_from_bytes

router = APIRouter(tags=['classifier'])

ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/jpg'}


@router.post('/classify', response_model=ClassifyResponse)
async def classify_image(
    request: Request,
    bin_id: str | None = None,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        f'classify:{client_ip}',
        limit=settings.classify_rate_limit_per_minute,
        window_seconds=60,
        detail='Too many classification requests. Please slow down.',
    )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail='Only JPEG and PNG images are supported')

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail='Uploaded file is empty')
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail='Uploaded file is too large')

    image = load_image_from_bytes(data, settings.image_size)
    service: ClassifierService = request.app.state.classifier_service
    best, top = service.predict(image, top_k=settings.top_k)

    stored = False
    if bin_id is not None:
        record = await get_bin(session, bin_id)
        if not record:
            raise HTTPException(status_code=404, detail='bin_id not found (register the bin first)')
        await add_classification(session, bin_id=bin_id, predicted_class=best.label, confidence=best.confidence)
        stored = True

    return ClassifyResponse(
        predicted_class=best.label,
        confidence=best.confidence,
        top_k=[TopKItem(label=item.label, confidence=item.confidence) for item in top],
        stored=stored,
    )
