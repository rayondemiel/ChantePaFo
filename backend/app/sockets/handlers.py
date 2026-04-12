import socketio
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import select

from app.ambiance.engine import get_ambiance_for_genre, get_ambiance_for_moment
from app.auth.service import decode_token
from app.database import async_session as session_factory
from app.database import get_redis
from app.game.engine import GameSession, registry
from app.logging_config import get_logger
from app.main import sio
from app.metrics import (
    GAMES_STARTED_TOTAL,
    PLAYERS_PER_ROOM,
    SOCKETIO_CONNECTIONS_ACTIVE,
    SOCKETIO_EVENTS_TOTAL,
)
from app.models import User
from app.music.deezer import DeezerClient
from app.rooms.schemas import PartialRoomSettings
from app.rooms.service import RoomService, public_room
from app.sockets.payloads import (
    GameEventPayload,
    JoinRoomPayload,
    ReactionPayload,
    RequestAmbiancePayload,
    SoundboardPayload,
    StartGamePayload,
    UpdateSettingsPayload,
)

logger = get_logger(__name__)

_ERR_NOT_IN_ROOM = "Not in room"
_ERR_ROOM_NOT_FOUND = "Room not found"
_ERR_ROOM_NOT_FOUND_OR_FULL = "Room not found or full"
_ERR_HOST_ONLY_SETTINGS = "Only the host can update settings"
_ERR_HOST_ONLY_START = "Only the host can start the game"
_ERR_NO_ACTIVE_SESSION = "No active game session for this room"

# In-memory game sessions, keyed by room code.
# Lives in the process — acceptable for single-worker MVP.
# Multi-worker deployments would require a shared session store (e.g. Redis).
_active_sessions: dict[str, GameSession] = {}


async def _handle_connect(sid: str, environ: dict[str, object], auth: object) -> None:
    if not auth or not isinstance(auth, dict):
        raise socketio.exceptions.ConnectionRefusedError("unauthorized")

    token = auth.get("token")
    if not token:
        raise socketio.exceptions.ConnectionRefusedError("unauthorized")

    try:
        payload = decode_token(token)
    except InvalidTokenError:
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


async def _handle_disconnect(sid: str) -> None:
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
                await sio.emit("room_updated", public_room(room), room=room_code)
        await redis.delete(f"player_room:{sid}")


async def _handle_join_room(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="join_room").inc()
    try:
        payload = JoinRoomPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid join_room payload"}, to=sid)
        return

    session = await sio.get_session(sid)
    user_id = session["user_id"]
    username = session.get("username") or user_id

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.join_room(payload.code, player_id=user_id, player_name=username)
    if not room:
        logger.warning("join_room failed: unknown or full room sid=%s code=%s", sid, payload.code)
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND_OR_FULL}, to=sid)
        return

    await sio.enter_room(sid, payload.code)
    await redis.set(f"player_room:{sid}", payload.code, ex=1800)
    logger.info("player joined room sid=%s room=%s user_id=%s", sid, payload.code, user_id)
    await sio.emit("room_updated", public_room(room), room=payload.code)


async def _handle_update_settings(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="update_settings").inc()
    try:
        payload = UpdateSettingsPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid update_settings payload"}, to=sid)
        return

    session = await sio.get_session(sid)
    user_id = session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    try:
        partial = PartialRoomSettings.model_validate(payload.settings)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid settings payload"}, to=sid)
        return

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.get_room(payload.code)
    if room is None:
        logger.warning("update_settings rejected: room not found code=%s", payload.code)
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND}, to=sid)
        return
    if room["host_id"] != user_id:
        logger.warning("update_settings rejected: not host room=%s user=%s", payload.code, user_id)
        await sio.emit("error", {"message": _ERR_HOST_ONLY_SETTINGS}, to=sid)
        return
    room = await svc.update_settings(payload.code, user_id, partial.model_dump(exclude_none=True))
    if room:
        logger.info("settings updated room=%s user=%s", payload.code, user_id)
        await sio.emit("room_updated", public_room(room), room=payload.code)


async def _handle_start_game(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="start_game").inc()
    try:
        payload = StartGamePayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid start_game payload"}, to=sid)
        return

    session = await sio.get_session(sid)
    user_id = session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.get_room(payload.code)
    if not room:
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND}, to=sid)
        return
    if room["host_id"] != user_id:
        logger.warning(
            "start_game rejected: not host sid=%s room=%s user=%s", sid, payload.code, user_id
        )
        await sio.emit("error", {"message": _ERR_HOST_ONLY_START}, to=sid)
        return

    mode_name: str = room.get("settings", {}).get("game_mode", "blindtest")
    try:
        mode = registry.create(mode_name)
    except KeyError:
        logger.warning("start_game rejected: unknown game mode=%s room=%s", mode_name, payload.code)
        await sio.emit("error", {"message": f"Unknown game mode: {mode_name}"}, to=sid)
        return

    player_count = len(room["players"])
    game_session = GameSession(mode)
    _active_sessions[payload.code] = game_session

    await game_session.start(
        players=room["players"],
        settings=room["settings"],
        track_provider=DeezerClient(),
    )

    updated_room = await svc.set_status(payload.code, "playing")
    if updated_room:
        logger.info("game started room=%s mode=%s", payload.code, mode_name)
        await sio.emit("game_started", public_room(updated_room), room=payload.code)

    state = game_session.get_state()
    await sio.emit("game_state", state, room=payload.code)
    await sio.emit("ambiance_update", get_ambiance_for_moment("countdown"), room=payload.code)

    GAMES_STARTED_TOTAL.labels(mode=mode_name).inc()
    PLAYERS_PER_ROOM.observe(player_count)


async def _handle_game_event(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="game_event").inc()
    try:
        payload = GameEventPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid game_event payload"}, to=sid)
        return

    sio_session = await sio.get_session(sid)
    user_id: str = sio_session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    game_session = _active_sessions.get(payload.code)
    if game_session is None:
        await sio.emit("error", {"message": _ERR_NO_ACTIVE_SESSION}, to=sid)
        return

    result = await game_session.handle_event(payload.event_type, user_id, payload.payload)
    if result is not None:
        await sio.emit("game_event_result", result, room=payload.code)

    state = game_session.get_state()
    await sio.emit("game_state", state, room=payload.code)

    if state.get("phase") == "finished":
        final = await game_session.end()
        await sio.emit("game_ended", final, room=payload.code)
        redis = get_redis()
        svc = RoomService(redis)
        await svc.set_status(payload.code, "lobby")
        del _active_sessions[payload.code]
        await sio.emit("ambiance_update", get_ambiance_for_moment("lobby"), room=payload.code)
        logger.info("game finished room=%s", payload.code)


async def _handle_request_ambiance(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="request_ambiance").inc()
    try:
        payload = RequestAmbiancePayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid request_ambiance payload"}, to=sid)
        return

    if payload.moment:
        ambiance = get_ambiance_for_moment(payload.moment)
    elif payload.genre:
        ambiance = get_ambiance_for_genre(payload.genre)
    else:
        ambiance = get_ambiance_for_moment("lobby")

    await sio.emit("ambiance_update", ambiance, to=sid)


async def _handle_reaction(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="reaction").inc()
    try:
        payload = ReactionPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid reaction payload"}, to=sid)
        return

    session = await sio.get_session(sid)
    user_id = session["user_id"]
    username = session["username"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    logger.debug(
        "reaction room=%s player=%s emoji=%s",
        payload.code,
        username,
        payload.emoji,
    )
    await sio.emit(
        "reaction_received",
        {
            "player_id": user_id,
            "player_name": username,
            "emoji": payload.emoji,
        },
        room=payload.code,
    )


async def _handle_soundboard(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="soundboard").inc()
    try:
        payload = SoundboardPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid soundboard payload"}, to=sid)
        return

    session = await sio.get_session(sid)
    username = session["username"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    logger.debug(
        "soundboard room=%s player=%s sound=%s",
        payload.code,
        username,
        payload.sound,
    )
    await sio.emit(
        "soundboard_played",
        {
            "player_name": username,
            "sound": payload.sound,
        },
        room=payload.code,
    )


def register_handlers() -> None:
    sio.on("connect", handler=_handle_connect)
    sio.on("disconnect", handler=_handle_disconnect)
    sio.on("join_room", handler=_handle_join_room)
    sio.on("update_settings", handler=_handle_update_settings)
    sio.on("start_game", handler=_handle_start_game)
    sio.on("game_event", handler=_handle_game_event)
    sio.on("request_ambiance", handler=_handle_request_ambiance)
    sio.on("reaction", handler=_handle_reaction)
    sio.on("soundboard", handler=_handle_soundboard)
