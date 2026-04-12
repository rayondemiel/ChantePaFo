"""Direct unit tests for get_current_user dependency.

Testing the dependency directly (as a coroutine) bypasses the async coverage
gap that affects FastAPI route handlers, ensuring the "user not found" branch
and other internal paths are tracked by coverage.py.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import get_current_user
from app.auth.service import create_access_token


@pytest.mark.asyncio
async def test_get_current_user_no_credentials(db_session):
    """Returns 401 when credentials are None."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=db_session)
    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_wrong_scheme(db_session):
    """Returns 401 when scheme is not 'bearer'."""
    creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="whatever")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session):
    """Returns 401 when token is not a valid JWT."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(db_session):
    """Returns 401 when the user_id in the token doesn't exist in the database."""
    import uuid

    token = create_access_token(user_id=str(uuid.uuid4()), username="ghost")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db_session)
    assert exc_info.value.status_code == 401
    assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_returns_user_on_valid_token(client, db_session):
    """Returns the User model when token is valid and user exists."""
    # Register a user via the API to ensure it's in the test DB
    resp = await client.post(
        "/auth/register",
        json={"username": "deptest", "email": "dep@example.com", "password": "password1"},
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    user_id = resp.json()["user_id"]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(credentials=creds, db=db_session)
    assert user.id == user_id
    assert user.username == "deptest"
