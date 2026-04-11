from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from app.auth.dependencies import get_current_user
from app.database import get_redis
from app.models import User
from app.rooms.schemas import RoomCreate, RoomJoin
from app.rooms.service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_room_service(redis: Redis = Depends(get_redis)) -> RoomService:
    return RoomService(redis)


def _public_room(room: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the room dict with private server-side fields removed."""
    public = {k: v for k, v in room.items() if k != "host_id"}
    return public


@router.post("", status_code=201)
async def create_room(
    req: RoomCreate,
    svc: RoomService = Depends(get_room_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    room = await svc.create_room(host_id=current_user.id, host_name=req.host_name)
    return {"room": _public_room(room)}


@router.get("/{code}")
async def get_room(
    code: str,
    svc: RoomService = Depends(get_room_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    room = await svc.get_room(code.upper())
    if not room:
        raise HTTPException(404, "Room not found")
    return _public_room(room)


@router.post("/{code}/join")
async def join_room(
    code: str,
    req: RoomJoin,
    svc: RoomService = Depends(get_room_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    room = await svc.join_room(code.upper(), player_id=current_user.id, player_name=req.player_name)
    if not room:
        raise HTTPException(404, "Room not found or full")
    return {"room": _public_room(room)}
