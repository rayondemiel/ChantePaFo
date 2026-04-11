from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chantepafo:chantepafo_dev@localhost:5432/chantepafo"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "dev-secret-change-in-production"
    deezer_api_base: str = "https://api.deezer.com"
    upload_dir: str = "uploads"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_prefix="CHANTEPAFO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
