import pytest
from app.auth.service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


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
            "password": "pass123",
        },
    )
    resp = await client.post(
        "/auth/register",
        json={
            "username": "alice",
            "email": "alice2@example.com",
            "password": "pass123",
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
