from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    database_url: str = "postgresql+asyncpg://uis_user:changeme_local@localhost:5432/urban_immune"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "epidemiology_docs"

    # OpenAI / Claude
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o"

    # 네이버 API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # 보안
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"

    # 서비스
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
