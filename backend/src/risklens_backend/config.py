from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "risklens-backend"
    backend_database_url: str = (
        "postgresql://risklens:risklens_dev_password@postgres:5432/risklens"
    )
    risk_service_url: str = "http://risk-service:8000"
    verifier_url: str = "http://ai-risk-verifier:8090"
    verifier_api_key: str = ""
    backend_review_threshold: float = Field(default=0.75, ge=0, le=1)
    backend_request_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
