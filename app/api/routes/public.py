from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stats")
async def public_stats():
    return {
        "platform": "DDSS Smart Waste",
        "supported_classes": 6,
        "features": [
            "Image classification",
            "Fill forecasting",
            "Decision support",
            "Route optimization",
            "Operational alerts",
            "Analytics",
        ],
    }