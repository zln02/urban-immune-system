from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"
    kafka_bootstrap: str = "localhost:9092"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    environment: str = "development"

    # .env 파일에 있는 추가 필드(DB_PASSWORD, STREAMLIT_PORT 등)가
    # 앱 기동을 막지 않도록 extra='ignore' 로 관용 (2026-04-21 수정)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
