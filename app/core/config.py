from __future__ import annotations
import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str
    api_prefix: str

    # Database (async SQLAlchemy / Postgres)
    # database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/ddss")
    database_url: str

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
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int = 60
    reset_token_expires_minutes: int = 30
    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://v0-ddss-hull.vercel.app",
    ]

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v.strip()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v.strip()

settings = Settings()
