import socketio
from jose import JWTError
from sqlalchemy import select

from app.auth.service import decode_token
from app.database import async_session as session_factory
from app.database import get_redis
from app.logging_config import get_logger
from app.main import sio
from app.metrics import SOCKETIO_CONNECTIONS_ACTIVE, SOCKETIO_EVENTS_TOTAL
from app.models import User
from app.rooms.service import RoomService

logger = get_logger(__name__)


def _public_room(room: dict) -> dict:
    """Return a copy of the room dict with private server-side fields removed."""
    return {k: v for k, v in room.items() if k != "host_id"}


def register_handlers():
    @sio.event
    async def connect(sid, environ, auth):
        if not auth or not isinstance(auth, dict):
            raise socketio.exceptions.ConnectionRefusedError("unauthorized")

        token = auth.get("token")
        if not token:
            raise socketio.exceptions.ConnectionRefusedError("unauthorized")

        try:
            payload = decode_token(token)
        except JWTError:
            raise socketio.exceptions.ConnectionRefusedError("unauthorized")

        user_id = payload.get("sub")
        username = payload.get("username")
        if not user_id or not username:
            raise socketio.exceptions.ConnectionRefusedError("unauthorized")

        async with session_factory() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

        if user is None:
            raise socketio.exceptions.ConnectionRefusedError("unauthorized")

        await sio.save_session(sid, {"user_id": user_id, "username": username})
        SOCKETIO_EVENTS_TOTAL.labels(event="connect").inc()
        SOCKETIO_CONNECTIONS_ACTIVE.inc()
        logger.info("client connected sid=%s user=%s", sid, username)

    @sio.event
    async def disconnect(sid):
        SOCKETIO_EVENTS_TOTAL.labels(event="disconnect").inc()
        SOCKETIO_CONNECTIONS_ACTIVE.dec()
        session = await sio.get_session(sid)
        user_id = session.get("user_id") if session else None
        logger.info("client disconnected sid=%s", sid)
        redis = get_redis()
        room_code = await redis.get(f"player_room:{sid}")
        if room_code:
            svc = RoomService(redis)
            if user_id:
                room = await svc.leave_room(room_code, user_id)
                if room:
                    logger.info(
                        "player left room sid=%s room=%s user_id=%s",
                        sid,
                        room_code,
                        user_id,
                    )
                    await sio.emit("room_updated", _public_room(room), room=room_code)
            await redis.delete(f"player_room:{sid}", f"player_id:{sid}")

    @sio.event
    async def join_room(sid, data):
        SOCKETIO_EVENTS_TOTAL.labels(event="join_room").inc()
        code = data["code"]
        session = await sio.get_session(sid)
        user_id = session["user_id"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.get_room(code)
        if not room:
            logger.warning("join_room failed: unknown room sid=%s code=%s", sid, code)
            await sio.emit("error", {"message": "Room not found"}, to=sid)
            return

        await sio.enter_room(sid, code)
        await redis.set(f"player_room:{sid}", code, ex=1800)
        await redis.set(f"player_id:{sid}", user_id, ex=1800)
        logger.info("player joined room sid=%s room=%s user_id=%s", sid, code, user_id)
        await sio.emit("room_updated", _public_room(room), room=code)

    @sio.event
    async def update_settings(sid, data):
        SOCKETIO_EVENTS_TOTAL.labels(event="update_settings").inc()
        code = data["code"]
        settings = data["settings"]
        session = await sio.get_session(sid)
        user_id = session["user_id"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.update_settings(code, user_id, settings)
        if room:
            logger.info("settings updated room=%s user=%s", code, user_id)
            await sio.emit("room_updated", _public_room(room), room=code)
        else:
            logger.warning(
                "update_settings rejected room=%s user=%s (not found or not host)",
                code,
                user_id,
            )

    @sio.event
    async def start_game(sid, data):
        SOCKETIO_EVENTS_TOTAL.labels(event="start_game").inc()
        code = data["code"]
        session = await sio.get_session(sid)
        user_id = session["user_id"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.get_room(code)
        if not room:
            await sio.emit("error", {"message": "Room not found"}, to=sid)
            return
        if room["host_id"] != user_id:
            logger.warning(
                "start_game rejected: not host sid=%s room=%s user=%s", sid, code, user_id
            )
            await sio.emit("error", {"message": "Only the host can start the game"}, to=sid)
            return
        room = await svc.set_status(code, "playing")
        if room:
            logger.info("game started room=%s", code)
            await sio.emit("game_started", _public_room(room), room=code)

    @sio.event
    async def reaction(sid, data):
        SOCKETIO_EVENTS_TOTAL.labels(event="reaction").inc()
        code = data["code"]
        session = await sio.get_session(sid)
        user_id = session["user_id"]
        username = session["username"]
        logger.debug(
            "reaction room=%s player=%s emoji=%s",
            code,
            username,
            data.get("emoji"),
        )
        await sio.emit(
            "reaction_received",
            {
                "player_id": user_id,
                "player_name": username,
                "emoji": data["emoji"],
            },
            room=code,
        )

    @sio.event
    async def soundboard(sid, data):
        SOCKETIO_EVENTS_TOTAL.labels(event="soundboard").inc()
        code = data["code"]
        session = await sio.get_session(sid)
        username = session["username"]
        logger.debug(
            "soundboard room=%s player=%s sound=%s",
            code,
            username,
            data.get("sound"),
        )
        await sio.emit(
            "soundboard_played",
            {
                "player_name": username,
                "sound": data["sound"],
            },
            room=code,
        )
