from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"
    kafka_bootstrap: str = "localhost:9092"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ml_service_url: str = "http://ml:8001"
    llm_model: str = "gpt-4o"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
