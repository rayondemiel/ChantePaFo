from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from app.auth.dependencies import get_current_user
from app.database import get_redis
from app.models import User
from app.rooms.schemas import RoomCreate, RoomJoin
from app.rooms.service import RoomService, public_room

router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_room_service(redis: Annotated[Redis, Depends(get_redis)]) -> RoomService:
    return RoomService(redis)


@router.post("", status_code=201)
async def create_room(
    req: RoomCreate,
    svc: Annotated[RoomService, Depends(get_room_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    room = await svc.create_room(host_id=current_user.id, host_name=req.host_name)
    return {"room": public_room(room)}


@router.get(
    "/{code}",
    responses={404: {"description": "Room not found"}},
)
async def get_room(
    code: str,
    svc: Annotated[RoomService, Depends(get_room_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    room = await svc.get_room(code.upper())
    if not room:
        raise HTTPException(404, "Room introuvable")
    return {"room": public_room(room)}


@router.post(
    "/{code}/join",
    responses={
        403: {"description": "Player was kicked from this room"},
        404: {"description": "Room not found or full"},
        409: {"description": "A game is in progress"},
    },
)
async def join_room(
    code: str,
    req: RoomJoin,
    svc: Annotated[RoomService, Depends(get_room_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    code = code.upper()
    if await svc.is_kicked(code, current_user.id):
        raise HTTPException(403, "Tu as été exclu de cette room")

    existing = await svc.get_room(code)
    already_in = any(p["id"] == current_user.id for p in (existing or {}).get("players", []))
    if existing and existing.get("status") == "playing" and not already_in:
        # A late joiner would sit in the game with no score slot — make them
        # wait for the lobby instead of silently becoming a ghost player.
        raise HTTPException(409, "Partie en cours, réessaie quand elle sera finie")

    room = await svc.join_room(code, player_id=current_user.id, player_name=req.player_name)
    if not room:
        raise HTTPException(404, "Room introuvable ou pleine")
    return {"room": public_room(room)}
