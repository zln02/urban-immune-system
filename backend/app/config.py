from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 운영 환경에서는 .env 또는 환경변수 DATABASE_URL로 덮어씌움
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"
    kafka_bootstrap: str = "localhost:9092"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
