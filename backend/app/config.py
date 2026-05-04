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

    # 3계층 앙상블 가중치 (합산 = 1.0)
    # L2 하수도가 가장 높음 — 임상 2~3주 선행 지표
    ensemble_weight_l1: float = 0.35   # OTC 약국 구매
    ensemble_weight_l2: float = 0.40   # 하수도 바이오마커
    ensemble_weight_l3: float = 0.25   # 검색 트렌드

    # ISMS-P 2.5.1·2.6.1·2.9.4 — HTTP 미들웨어
    # api_keys 는 CSV 또는 list 로 .env 에서 주입 (production 에서 1개 이상 필수)
    api_keys: list[str] = []
    rate_limit_per_minute: int = 120
    rate_limit_burst: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("allowed_origins", "api_keys", mode="before")
    @classmethod
    def parse_csv(cls, value: str | list[str]) -> list[str]:
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
        if is_production and not self.api_keys:
            raise ValueError("api_keys must contain at least one key in production (ISMS-P 2.5.1)")
        return self


settings = Settings()
