from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 운영 환경에서는 .env 또는 환경변수 DATABASE_URL로 덮어씌움
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"
    kafka_bootstrap: str = "localhost:9092"
    qdrant_url: str = "http://localhost:6333"
    ml_service_url: str = "http://ml:8001"
    anthropic_api_key: str = ""
    # CLAUDE.md 의 RAG 리포트 기본 모델 — Haiku 4.5 (비용·지연 균형).
    # Sonnet/Opus 가 필요한 운영 환경은 .env 의 LLM_MODEL 로 override.
    llm_model: str = "claude-haiku-4-5-20251001"
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8501"]

    # 3계층 앙상블 가중치 (합산 = 1.0)
    # L2 하수도가 가장 높음 — 임상 2~3주 선행 지표
    ensemble_weight_l1: float = 0.35  # OTC 약국 구매
    ensemble_weight_l2: float = 0.40  # 하수도 바이오마커
    ensemble_weight_l3: float = 0.25  # 검색 트렌드

    # ISMS-P 2.5.1·2.6.1·2.9.4 — HTTP 미들웨어
    # api_keys 는 CSV 또는 list 로 .env 에서 주입 (production 에서 1개 이상 필수)
    api_keys: list[str] = []
    rate_limit_per_minute: int = 120
    rate_limit_burst: int = 30

    # 지역별 Gate B layer threshold (캘리브레이션 파라미터)
    # 알고리즘 변경 없음 — 약신호 지역의 과도 차단 완화 목적
    # 기본값: 14개 강한 지역 30.0 / 약한 3지역(충청북도·대구광역시·경상북도) 12.0
    regional_layer_thresholds: dict[str, float] = Field(
        default={
            "충청북도": 12.0,
            "대구광역시": 12.0,
            "경상북도": 12.0,
        },
        description="지역별 Gate B layer threshold (기본값 30.0, 명시된 지역만 override)",
    )
    default_layer_threshold: float = Field(
        default=30.0,
        description="명시되지 않은 지역의 Gate B threshold",
    )

    # 지역별 YELLOW 경보 composite 임계값 (calibration parameter)
    # 충북: composite ≥ 20, 대구/경북: composite ≥ 25, 나머지 14지역: 30 (기본값)
    regional_composite_thresholds: dict[str, float] = Field(
        default={
            "충청북도": 20.0,
            "대구광역시": 25.0,
            "경상북도": 25.0,
        },
        description="지역별 YELLOW 진입 composite 임계값 (기본값 30.0)",
    )
    default_composite_threshold: float = Field(
        default=30.0,
        description="명시되지 않은 지역의 composite YELLOW 임계값",
    )

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
        # ISMS-P 2.10.1 — ANTHROPIC_API_KEY 누락 시 production 거부
        if is_production and not self.anthropic_api_key:
            raise ValueError("anthropic_api_key must be set in production (ISMS-P 2.10.1)")
        # ISMS-P 2.1.1 — DEBUG 모드 production 강제 off (정보 노출 방지)
        if is_production and getattr(self, "debug", False):
            raise ValueError("debug must be disabled in production (ISMS-P 2.1.1)")
        # ISMS-P 2.10.1 — CORS 와일드카드 production 거부
        if is_production and "*" in self.allowed_origins:
            raise ValueError("CORS allow_origins='*' is forbidden in production (ISMS-P 2.10.1)")
        return self


settings = Settings()
