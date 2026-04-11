from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_FORBIDDEN_SECRETS = {
    "",
    "dev-secret-change-in-production",
    "change-me",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chantepafo:chantepafo_dev@localhost:5432/chantepafo"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = Field(..., min_length=32)
    deezer_api_base: str = "https://api.deezer.com"
    upload_dir: str = "uploads"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="CHANTEPAFO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("secret_key")
    @classmethod
    def _reject_weak_secret(cls, v: str) -> str:
        if v.strip().lower() in _FORBIDDEN_SECRETS:
            raise ValueError(
                "CHANTEPAFO_SECRET_KEY must be set to a non-default value. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return v


settings = Settings()  # type: ignore[call-arg]
