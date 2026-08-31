from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RISK_", env_file=".env", extra="ignore", case_sensitive=False
    )

    service_name: str = "risklens-risk-service"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    api_key: str | None = None

    database_url: str = "postgresql://risklens:risklens_dev_password@localhost:5432/risklens"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "risklens_dev_password"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    verifier_url: str = "http://localhost:8090"
    verifier_api_key: str | None = None
    require_verifier: bool = True

    vector_size: int = Field(default=384, ge=32, le=4096)
    history_limit: int = Field(default=500, ge=10, le=5000)
    request_timeout_seconds: float = Field(default=1.5, gt=0, le=10)
    review_threshold: float = Field(default=0.60, ge=0, le=1)
    hold_threshold: float = Field(default=0.82, ge=0, le=1)
    decline_threshold: float = Field(default=0.95, ge=0, le=1)
    similarity_threshold: float = Field(default=0.15, ge=0, le=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
