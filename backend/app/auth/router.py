from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.auth.service import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=201,
    responses={409: {"description": "Username or email already exists"}},
)
async def register(
    req: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Username or email already exists")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Lost the race against a concurrent register of the same slug: the
        # SELECT above passed for both, the unique index settles it.
        await db.rollback()
        raise HTTPException(409, "Username or email already exists") from None
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return TokenResponse(token=token, username=user.username, user_id=user.id)


@router.post(
    "/login",
    responses={401: {"description": "Invalid credentials"}},
)
async def login(
    req: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(user.id, user.username)
    return TokenResponse(token=token, username=user.username, user_id=user.id)
