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
