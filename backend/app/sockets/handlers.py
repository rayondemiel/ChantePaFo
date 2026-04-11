from app.database import get_redis
from app.logging_config import get_logger
from app.main import sio
from app.rooms.service import RoomService

logger = get_logger(__name__)


def register_handlers():
    @sio.event
    async def connect(sid, environ):
        logger.info("client connected sid=%s", sid)

    @sio.event
    async def disconnect(sid):
        logger.info("client disconnected sid=%s", sid)
        redis = get_redis()
        room_code = await redis.get(f"player_room:{sid}")
        if room_code:
            svc = RoomService(redis)
            player_id = await redis.get(f"player_id:{sid}")
            if player_id:
                room = await svc.leave_room(room_code, player_id)
                if room:
                    logger.info(
                        "player left room sid=%s room=%s player_id=%s",
                        sid,
                        room_code,
                        player_id,
                    )
                    await sio.emit("room_updated", room, room=room_code)
            await redis.delete(f"player_room:{sid}", f"player_id:{sid}")

    @sio.event
    async def join_room(sid, data):
        code = data["code"]
        player_id = data["player_id"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.get_room(code)
        if not room:
            logger.warning("join_room failed: unknown room sid=%s code=%s", sid, code)
            await sio.emit("error", {"message": "Room not found"}, to=sid)
            return

        await sio.enter_room(sid, code)
        await redis.set(f"player_room:{sid}", code, ex=1800)
        await redis.set(f"player_id:{sid}", player_id, ex=1800)
        logger.info("player joined room sid=%s room=%s player_id=%s", sid, code, player_id)
        await sio.emit("room_updated", room, room=code)

    @sio.event
    async def update_settings(sid, data):
        code = data["code"]
        host_id = data["host_id"]
        settings = data["settings"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.update_settings(code, host_id, settings)
        if room:
            logger.info("settings updated room=%s host=%s", code, host_id)
            await sio.emit("room_updated", room, room=code)
        else:
            logger.warning(
                "update_settings rejected room=%s host=%s (not found or not host)",
                code,
                host_id,
            )

    @sio.event
    async def start_game(sid, data):
        code = data["code"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.set_status(code, "playing")
        if room:
            logger.info("game started room=%s", code)
            await sio.emit("game_started", room, room=code)

    @sio.event
    async def reaction(sid, data):
        code = data["code"]
        logger.debug(
            "reaction room=%s player=%s emoji=%s",
            code,
            data.get("player_name"),
            data.get("emoji"),
        )
        await sio.emit(
            "reaction_received",
            {
                "player_id": data["player_id"],
                "player_name": data["player_name"],
                "emoji": data["emoji"],
            },
            room=code,
        )

    @sio.event
    async def soundboard(sid, data):
        code = data["code"]
        logger.debug(
            "soundboard room=%s player=%s sound=%s",
            code,
            data.get("player_name"),
            data.get("sound"),
        )
        await sio.emit(
            "soundboard_played",
            {
                "player_name": data["player_name"],
                "sound": data["sound"],
            },
            room=code,
        )
