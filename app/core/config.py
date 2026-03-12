from __future__ import annotations
import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ddss-smart-waste"
    api_prefix: str = "/api/v1"

    # Database (async SQLAlchemy / Postgres)
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/ddss")

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # Model paths
    classifier_model_path: str = "models/densenet121_final.keras"
    forecast_model_path: str = "models/fill_forecast_rf.pkl"

    # Inference
    image_size: int = 224
    top_k: int = 3

    # DDSS weights
    w_fill: float = 0.5
    w_last_collection: float = 0.3
    w_uncertainty: float = 0.2

    # Routing
    truck_capacity: float = 300.0
    epsilon: float = 1e-6

    # DDSS behavior
    critical_fill_threshold: float = 90.0
    overdue_hours_threshold: float = 36.0
    low_confidence_threshold: float = 0.6

    #Authentication
    jwt_secret: str = os.getenv("JWT_SECRET", "053e22b1b73247c293a7e258645bd9030a34f08ffdf9c2496a294fd9a782df5b")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expires_minutes: int = int(os.getenv("JWT_EXPIRES_MINUTES", "1440"))
    reset_token_expires_minutes: int = int(os.getenv("RESET_TOKEN_EXPIRES_MINUTES", "30"))

settings = Settings()
