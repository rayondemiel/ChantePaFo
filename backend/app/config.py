import sys
from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_FORBIDDEN_SECRETS = {
    "",
    "dev-secret-change-in-production",
    "change-me",
    "changeme",
    "secret",
    "replace-me-with-32-bytes-hex-from-secrets-token-hex",
}

_FORBIDDEN_METRICS_PASSWORDS = {
    "",
    "metrics",
    "password",
    "changeme",
    "admin",
    "replace-me",
    "replace-me-with-16-plus-char-random-string",
}


class Settings(BaseSettings):
    database_url: str = Field(...)
    redis_url: str = Field(...)
    secret_key: str = Field(..., min_length=32)
    metrics_username: str = "metrics"
    metrics_password: str = Field(..., min_length=16)
    deezer_api_base: str = "https://api.deezer.com"
    upload_dir: str = "uploads"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
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

    @field_validator("metrics_password")
    @classmethod
    def _reject_weak_metrics_password(cls, v: str) -> str:
        if v.strip().lower() in _FORBIDDEN_METRICS_PASSWORDS:
            raise ValueError(
                "CHANTEPAFO_METRICS_PASSWORD must be set to a non-placeholder value "
                "of at least 16 characters."
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def _reject_wildcard(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                "cors_origins must not contain '*' — Starlette forbids this when "
                "allow_credentials=True (which this app enables). List explicit origins."
            )
        return v


try:
    settings = Settings()  # type: ignore[call-arg]
except ValidationError as e:
    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if not _env_file.exists():
        print(
            f"\n\033[1;31mERROR: .env file not found at {_env_file}\033[0m\n"
            f"Copy the example and fill in the values:\n"
            f"  cp .env.example .env\n",
            file=sys.stderr,
        )
    else:
        print(
            f"\n\033[1;31mERROR: Invalid configuration in {_env_file}\033[0m\n{e}\n",
            file=sys.stderr,
        )
    sys.exit(1)
