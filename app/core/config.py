from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'DDSS Smart Waste Backend'
    api_prefix: str = '/api/v1'

    database_url: str

    classifier_model_path: str = 'models/densenet121_final.keras'
    forecast_model_path: str = 'models/fill_forecast_rf.pkl'

    image_size: int = 224
    top_k: int = 3
    max_upload_size_bytes: int = 10 * 1024 * 1024

    w_fill: float = 0.5
    w_last_collection: float = 0.3
    w_uncertainty: float = 0.2

    truck_capacity: float = 300.0
    epsilon: float = 1e-6

    critical_fill_threshold: float = 90.0
    default_collection_interval_days: int = 7
    collection_due_soon_ratio: float = 0.85
    collection_overdue_ratio: float = 1.0
    collection_critical_ratio: float = 1.15
    low_confidence_threshold: float = 0.6

    jwt_secret: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60
    reset_token_expires_minutes: int = 30
    token_cookie_name: str = 'ddss_access_token'
    cookie_secure: bool = False
    cookie_samesite: str = 'lax'

    cors_origins: list[str] = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'https://v0-ddss-hull.vercel.app',
        'https://v0-smart-waste-landing-page-woad.vercel.app',
    ]

    resend_api_key: str | None = None
    mail_from: str = Field(default='DDSS Smart Waste <noreply@yourdomain.com>', alias='MAIL_FROM')
    app_base_url: str = 'http://localhost:3000'

    internal_api_key: str | None = Field(default=None, alias='INTERNAL_API_KEY')

    log_level: str = 'INFO'
    log_json: bool = False

    auth_rate_limit_window_seconds: int = 300
    auth_login_max_attempts: int = 5
    reset_request_max_attempts: int = 3
    reset_verify_max_attempts: int = 6
    classify_rate_limit_per_minute: int = 30
    ddss_run_rate_limit_per_minute: int = 10
    route_plan_rate_limit_per_minute: int = 10

    @field_validator('jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 32:
            raise ValueError('JWT_SECRET must be at least 32 characters long')
        return value

    @field_validator('api_prefix')
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith('/'):
            raise ValueError("API_PREFIX must start with '/'")
        return value.rstrip('/') or '/'

    @field_validator('cors_origins', mode='before')
    @classmethod
    def normalize_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator('cookie_samesite')
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {'lax', 'strict', 'none'}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        return value


settings = Settings()
