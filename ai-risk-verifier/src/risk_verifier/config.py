from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VERIFIER_", env_file=".env", extra="ignore", case_sensitive=False
    )

    service_name: str = "risklens-ai-risk-verifier"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8090
    log_level: str = "INFO"
    api_key: str | None = None

    database_url: str = "postgresql://risklens:risklens_dev_password@localhost:5432/risklens"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    vector_size: int = Field(default=384, ge=32, le=4096)
    retrieval_limit: int = Field(default=5, ge=1, le=20)
    retrieval_score_threshold: float = Field(default=0.08, ge=0, le=1)
    confirmed_case_similarity_threshold: float = Field(default=0.25, ge=0, le=1)
    false_positive_similarity_threshold: float = Field(default=0.32, ge=0, le=1)
    request_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    seed_default_policies: bool = True
    backfill_reviewed_cases: bool = True
    memory_reconciliation_interval_seconds: float = Field(default=300, ge=10, le=86400)


@lru_cache
def get_settings() -> Settings:
    return Settings()
