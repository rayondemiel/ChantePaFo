from datetime import datetime, timedelta, timezone

import jwt
import pytest
from jwt.exceptions import InvalidTokenError

from app.auth.service import (
    ALGORITHM,
    ISSUER,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings


def test_hash_and_verify_password():
    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert verify_password("mypassword123", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_token():
    token = create_access_token(user_id="user-123", username="alice")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["username"] == "alice"


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "token" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password1",
        },
    )
    resp = await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice2@example.com",
            "password": "password1",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    resp = await client.post(
        "/auth/login",
        json={
            "username": "alice",
            "password": "securepass123",
        },
    )
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    resp = await client.post(
        "/auth/login",
        json={
            "username": "alice",
            "password": "wrongpass",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_rejects_short_password(client):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "short",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_invalid_email(client):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "bob",
            "email": "not-an-email",
            "password": "password1",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_invalid_username(client):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "bad user!",
            "email": "bob@example.com",
            "password": "password1",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_oversize_password(client):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "x" * 73,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Token claims
# ---------------------------------------------------------------------------


def test_token_includes_iat_and_iss():
    token = create_access_token(user_id="u1", username="testuser")
    payload = decode_token(token)
    assert "iat" in payload
    assert payload["iss"] == ISSUER


# ---------------------------------------------------------------------------
# get_current_user dependency boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_header(client):
    """Any protected endpoint returns 401 when Authorization header is absent."""
    resp = await client.post("/rooms", json={"host_name": "Alice"})
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(client):
    """A malformed JWT token returns 401."""
    resp = await client.post(
        "/rooms",
        json={"host_name": "Alice"},
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_expired_token(client):
    """A well-formed but expired token returns 401."""
    expired_payload = {
        "sub": "user-expired",
        "username": "ghost",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "iss": ISSUER,
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=ALGORITHM)
    resp = await client.post(
        "/rooms",
        json={"host_name": "Alice"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_token_without_sub(client):
    """Token missing the 'sub' claim is rejected as invalid payload."""
    bad_payload = {
        "username": "ghost",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "iss": ISSUER,
    }
    # Encode without the "require" validation (decode_token will reject on decode)
    bad_token = jwt.encode(bad_payload, settings.secret_key, algorithm=ALGORITHM)
    resp = await client.post(
        "/rooms",
        json={"host_name": "Alice"},
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_token_for_deleted_user(client):
    """A valid token whose user_id doesn't exist in the DB is rejected."""
    # Token for a user that was never registered
    ghost_token = create_access_token(user_id="nonexistent-user-id", username="ghost")
    resp = await client.post(
        "/rooms",
        json={"host_name": "Alice"},
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert resp.status_code == 401


def test_decode_token_rejects_wrong_issuer():
    """A token signed with the correct key but a different issuer is rejected."""
    bad_payload = {
        "sub": "u1",
        "username": "x",
        "iat": datetime.now(timezone.utc),
        "iss": "evil-issuer",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    bad_token = jwt.encode(bad_payload, settings.secret_key, algorithm=ALGORITHM)
    with pytest.raises(InvalidTokenError):
        decode_token(bad_token)
