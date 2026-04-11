import uuid

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from app.database import get_redis
from app.rooms.schemas import RoomCreate, RoomJoin
from app.rooms.service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_room_service(redis: Redis = Depends(get_redis)) -> RoomService:
    return RoomService(redis)


@router.post("", status_code=201)
async def create_room(req: RoomCreate, svc: RoomService = Depends(get_room_service)):
    host_id = str(uuid.uuid4())
    room = await svc.create_room(host_id=host_id, host_name=req.host_name)
    return {"room": room, "player_id": host_id}


@router.get("/{code}")
async def get_room(code: str, svc: RoomService = Depends(get_room_service)):
    room = await svc.get_room(code.upper())
    if not room:
        raise HTTPException(404, "Room not found")
    return room


@router.post("/{code}/join")
async def join_room(
    code: str, req: RoomJoin, svc: RoomService = Depends(get_room_service)
):
    player_id = str(uuid.uuid4())
    room = await svc.join_room(
        code.upper(), player_id=player_id, player_name=req.player_name
    )
    if not room:
        raise HTTPException(404, "Room not found or full")
    return {"room": room, "player_id": player_id}
