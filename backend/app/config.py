from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 운영 환경에서는 .env 또는 환경변수 DATABASE_URL로 덮어씌움
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"
    kafka_bootstrap: str = "localhost:9092"
    qdrant_url: str = "http://localhost:6333"
    ml_service_url: str = "http://ml:8001"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8501"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_environment_settings(self) -> Settings:
        is_production = self.environment.lower() == "production"
        if is_production and "changeme" in self.database_url:
            raise ValueError("database_url must not use placeholder credentials in production")
        if is_production and self.ml_service_url.startswith("http://"):
            raise ValueError("ml_service_url must use https in production")
        return self


settings = Settings()
