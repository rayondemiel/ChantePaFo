import pytest
from pydantic import ValidationError

from app.config import Settings


def test_secret_key_rejects_env_example_placeholder():
    with pytest.raises(ValidationError):
        Settings(
            secret_key="replace-me-with-32-bytes-hex-from-secrets-token-hex",
            metrics_password="a-valid-long-enough-metrics-password",
        )


def test_secret_key_accepts_strong_value():
    s = Settings(
        secret_key="a" * 64,  # 64-char random-looking value
        metrics_password="a-valid-long-enough-metrics-password",
    )
    assert s.secret_key == "a" * 64


def test_secret_key_rejects_known_placeholders():
    for placeholder in [
        "dev-secret-change-in-production",
        "change-me",
        "changeme",
        "secret",
    ]:
        with pytest.raises(ValidationError):
            Settings(
                secret_key=placeholder,
                metrics_password="a-valid-long-enough-metrics-password",
            )


def test_cors_validator_rejects_wildcard():
    with pytest.raises(ValidationError):
        Settings(
            secret_key="a" * 64,
            metrics_password="a-valid-long-enough-metrics-password",
            cors_origins=["*"],
        )


def test_format_validation_errors_does_not_leak_secret_value():
    """Misconfigured secrets must NOT appear in the formatted error output."""
    from app.config import format_validation_errors

    leaky_secret = "leak-me-32"  # < 32 chars → triggers min_length error
    leaky_password = "short-pw"  # < 16 chars → triggers min_length error
    with pytest.raises(ValidationError) as exc_info:
        Settings(secret_key=leaky_secret, metrics_password=leaky_password)

    formatted = "\n".join(format_validation_errors(exc_info.value))
    assert leaky_secret not in formatted
    assert leaky_password not in formatted
    assert "secret_key" in formatted
    assert "metrics_password" in formatted
