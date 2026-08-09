import asyncio
from typing import Any, cast

import socketio
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import select

from app.ambiance.engine import get_ambiance_for_genre, get_ambiance_for_moment
from app.auth.service import decode_token
from app.database import async_session as session_factory
from app.database import get_redis
from app.game.blindtest import (
    PHASE_FINISHED,
    PHASE_PLAYING,
    PHASE_PLAYING_REVEAL,
    PHASE_ROUND_PAUSE,
    BlindtestMode,
)
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
from app.music.deezer import RoomScopedDeezerClient
from app.rooms.schemas import PartialRoomSettings
from app.rooms.service import ROOM_TTL, RoomService, public_room
from app.sockets.payloads import (
    AnswerPayload,
    GameEventPayload,
    JoinRoomPayload,
    KickPlayerPayload,
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
_ERR_KICKED = "You have been removed from this room"
_ERR_HOST_ONLY_LOBBY = "Only the host can return to lobby"
_ERR_HOST_ONLY_REPLAY = "Only the host can replay"
_ERR_REPLAY_COOLDOWN = "Please wait before replaying again"

# Minimum delay between replay_game requests per room. Prevents a host from
# spamming the endpoint and hammering the Deezer API repeatedly.
_REPLAY_COOLDOWN_SECONDS = 5

# Upper bound on any text fed to fuzzy_match() (Levenshtein is O(n*m)).
_MAX_FUZZY_TEXT_LEN = 200


def _kicked_key(code: str, user_id: str) -> str:
    return f"kicked:{code}:{user_id}"


def _room_sids_key(code: str) -> str:
    return f"room_sids:{code}"


# In-memory game sessions, keyed by room code.
# Lives in the process — acceptable for single-worker MVP.
# Multi-worker deployments would require a shared session store (e.g. Redis).
_active_sessions: dict[str, GameSession] = {}

# Per-room asyncio tasks that drive the blindtest round timeline (playing →
# playing_reveal → round_pause → next round). Stored so they can be cancelled
# when the room is cleaned up or a new game starts.
_round_timers: dict[str, asyncio.Task[None]] = {}

# Reveal lasts 5s (music keeps playing), then a 2s silent pause before the
# next round. Tweak these constants if the UX needs adjusting.
_REVEAL_DURATION_SECONDS = 5
_ROUND_PAUSE_DURATION_SECONDS = 2


def _cancel_round_timer(code: str) -> None:
    task = _round_timers.pop(code, None)
    if task is not None and not task.done():
        task.cancel()


async def _finish_blindtest_game(code: str) -> None:
    """End the blindtest game, emit game_ended, and reset room status to lobby."""
    existing = _active_sessions.pop(code, None)
    if existing is None:
        return  # another coroutine already handled the finish
    final = await existing.end()
    await sio.emit("game_ended", final, room=code)
    redis = get_redis()
    svc = RoomService(redis)
    await svc.set_status(code, "lobby")
    await sio.emit("ambiance_update", get_ambiance_for_moment("lobby"), room=code)
    logger.info("game finished room=%s", code)


async def _emit_round_ambiance(code: str, mode: BlindtestMode) -> None:
    """Emit an ambiance_update tailored to the current round's genre.

    Called whenever a new round starts so the front-end orbs/glows reflect
    the music being played (palette + intensity per genre, see
    app/ambiance/engine.py). Without this, the ambiance stays frozen on
    whatever the last emit was (countdown by default).
    """
    round_idx = int(mode.state.get("current_round", 0))
    if 0 <= round_idx < len(mode.tracks):
        genre = mode.tracks[round_idx].get("genre", "")
        if genre:
            await sio.emit("ambiance_update", get_ambiance_for_genre(genre), room=code)


async def _run_round_timeline(code: str, game_session: GameSession) -> None:
    """Drive the blindtest round timeline via asyncio sleeps.

    Loops through: playing → playing_reveal → round_pause → playing (next).
    Bails out on phase mismatch (defensive), and triggers game-end cleanup on
    transition to finished.
    """
    mode = game_session.mode
    if not isinstance(mode, BlindtestMode):
        return

    try:
        extract_duration = int(mode.state.get("extract_duration", 30))
        playing_duration = max(extract_duration - _REVEAL_DURATION_SECONDS, 0)

        # Round 1 already entered PHASE_PLAYING via countdown_done — emit its
        # ambiance now (the countdown_done handler doesn't know the track).
        await _emit_round_ambiance(code, mode)

        while True:
            # Phase: playing — wait for the answer window to close.
            await asyncio.sleep(playing_duration)
            if mode.state.get("phase") != PHASE_PLAYING:
                return
            mode.advance_to_reveal()
            await sio.emit("game_state", game_session.get_state(), room=code)

            # Phase: playing_reveal — music continues, answers locked.
            await asyncio.sleep(_REVEAL_DURATION_SECONDS)
            if mode.state.get("phase") != PHASE_PLAYING_REVEAL:
                return
            mode.advance_to_pause()
            await sio.emit("game_state", game_session.get_state(), room=code)

            # Phase: round_pause — frontend stops audio for a brief silence.
            await asyncio.sleep(_ROUND_PAUSE_DURATION_SECONDS)
            if mode.state.get("phase") != PHASE_ROUND_PAUSE:
                return
            mode.advance_to_next_round()
            await sio.emit("game_state", game_session.get_state(), room=code)

            if mode.state.get("phase") == PHASE_FINISHED:
                await _finish_blindtest_game(code)
                return
            # New round just loaded → push its ambiance so the orbs reflect
            # the new genre (otherwise they stay on the previous one).
            await _emit_round_ambiance(code, mode)
            # Otherwise we're back in PHASE_PLAYING for the next round; loop.
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("round timeline crashed for room=%s: %s", code, exc)


def _spawn_round_timer(code: str, game_session: GameSession) -> None:
    """Spawn (or replace) the round timeline task for a room."""
    _cancel_round_timer(code)
    task = asyncio.create_task(_run_round_timeline(code, game_session))
    _round_timers[code] = task

    def _cleanup(_t: asyncio.Task[None]) -> None:
        # Only drop ourselves if we're still the registered timer (avoid
        # racing with a newer timer that replaced us).
        if _round_timers.get(code) is _t:
            _round_timers.pop(code, None)

    task.add_done_callback(_cleanup)


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
        await cast("Any", redis.srem(_room_sids_key(room_code), sid))

        # Cleanup: if no players left in the room, end the game session
        if room_code in _active_sessions:
            room_after = await svc.get_room(room_code)
            if not room_after or not room_after.get("players"):
                del _active_sessions[room_code]
                _cancel_round_timer(room_code)
                logger.info("game session cleaned up (empty room) room=%s", room_code)


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

    # Reject rejoin attempts from kicked users until the ban key expires.
    if await redis.exists(_kicked_key(payload.code, user_id)):
        logger.warning(
            "join_room blocked (kicked) sid=%s room=%s user_id=%s",
            sid,
            payload.code,
            user_id,
        )
        await sio.emit("error", {"message": _ERR_KICKED}, to=sid)
        return

    svc = RoomService(redis)
    room = await svc.join_room(payload.code, player_id=user_id, player_name=username)
    if not room:
        logger.warning("join_room failed: unknown or full room sid=%s code=%s", sid, payload.code)
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND_OR_FULL}, to=sid)
        return

    await sio.enter_room(sid, payload.code)
    # Track the sid in a reverse-lookup set so kicks can find every live
    # socket for a given user_id.
    await cast("Any", redis.sadd(_room_sids_key(payload.code), sid))
    await redis.expire(_room_sids_key(payload.code), ROOM_TTL)
    await redis.set(f"player_room:{sid}", payload.code, ex=ROOM_TTL)
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
    # Defensive: cancel any leftover timer from a previous game in this room.
    _cancel_round_timer(payload.code)
    game_session = GameSession(mode)
    _active_sessions[payload.code] = game_session

    await game_session.start(
        players=room["players"],
        settings=room["settings"],
        track_provider=RoomScopedDeezerClient(redis, payload.code),
    )

    # Defensive: if the mode finished immediately (e.g. blindtest with zero
    # tracks because Deezer returned nothing), don't transition the room to
    # "playing" — finalize and stay in lobby with a clear error.
    if game_session.get_state().get("phase") == PHASE_FINISHED:
        logger.warning("start_game aborted: no tracks available room=%s", payload.code)
        _active_sessions.pop(payload.code, None)
        await sio.emit("error", {"message": "No tracks available for these settings"}, to=sid)
        return

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

    # Cap text length on any event that ends up in fuzzy_match() to prevent
    # Levenshtein-DoS via huge payloads (a 1MB string against a 30-char title
    # would block the asyncio worker for seconds). Server is also authoritative
    # for timing on blindtest answers — any client-supplied time_ms is
    # discarded, BlindtestMode recomputes from its own monotonic clock.
    event_payload: dict[str, Any] = payload.payload
    if payload.event_type == "answer":
        try:
            answer = AnswerPayload.model_validate(event_payload)
        except ValidationError:
            await sio.emit("error", {"message": "Invalid answer payload"}, to=sid)
            return
        event_payload = {"text": answer.text}
    elif payload.event_type in ("guess", "submit_step"):
        # Karaoke (guess) and telephone (submit_step write) feed text into
        # fuzzy_match too. submit_step also carries audio_url for the singing
        # variant — pass it through unchanged but bound the text field.
        text = event_payload.get("text", "")
        if isinstance(text, str) and len(text) > _MAX_FUZZY_TEXT_LEN:
            await sio.emit("error", {"message": "Answer too long"}, to=sid)
            return

    result = await game_session.handle_event(payload.event_type, user_id, event_payload)
    if result is not None:
        if payload.event_type == "answer" and isinstance(game_session.mode, BlindtestMode):
            if result.get("title_match") or result.get("artist_match"):
                match_type = (
                    "bonus"
                    if result.get("bonus")
                    else ("title" if result.get("title_match") else "artist")
                )
                await sio.emit(
                    "player_match",
                    {
                        "player_id": user_id,
                        "time_ms": result.get("time_ms", 0),
                        "match_type": match_type,
                    },
                    room=payload.code,
                )
            if result.get("bonus") is True:
                mode = game_session.mode
                round_idx = int(mode.state.get("current_round", 0))
                if 0 <= round_idx < len(mode.tracks):
                    track = mode.tracks[round_idx]
                    result["correct_title"] = track["title"]
                    result["correct_artist"] = track["artist"]
                    result["cover_url"] = track.get("cover_url", "")
        await sio.emit("game_event_result", result, to=sid)

    state = game_session.get_state()
    await sio.emit("game_state", state, room=payload.code)

    # Blindtest auto-advance: as soon as we enter the "playing" phase (after
    # countdown_done), spawn the timeline task that drives reveal/pause/next.
    if (
        payload.event_type == "countdown_done"
        and state.get("phase") == PHASE_PLAYING
        and isinstance(game_session.mode, BlindtestMode)
    ):
        _spawn_round_timer(payload.code, game_session)

    # Defensive: legacy finish path (other game modes still drive game-end via
    # handle_event). Blindtest finishes via the timeline coroutine instead.
    if state.get("phase") == PHASE_FINISHED:
        _cancel_round_timer(payload.code)
        await _finish_blindtest_game(payload.code)


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


async def _handle_kick_player(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="kick_player").inc()
    try:
        payload = KickPlayerPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid kick_player payload"}, to=sid)
        return

    sio_session = await sio.get_session(sid)
    user_id: str = sio_session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.get_room(payload.code)
    if room is None:
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND}, to=sid)
        return
    if room["host_id"] != user_id:
        await sio.emit("error", {"message": "Only the host can kick players"}, to=sid)
        return
    if payload.player_id == user_id:
        await sio.emit("error", {"message": "Cannot kick yourself"}, to=sid)
        return

    # The target must actually be in the room — otherwise the host could
    # inject any player_id into the player_kicked broadcast.
    member_ids = {p["id"] for p in room.get("players", [])}
    if payload.player_id not in member_ids:
        await sio.emit("error", {"message": "Player is not in this room"}, to=sid)
        return

    # Persist a ban key so the target cannot re-join via join_room.
    await redis.set(_kicked_key(payload.code, payload.player_id), "1", ex=ROOM_TTL)

    # Find every live socket for the target user — we need them for the
    # disconnect loop below, but only AFTER broadcasting player_kicked.
    raw_sids: set[str] = await cast("Any", redis.smembers(_room_sids_key(payload.code)))
    target_sids: list[str] = []
    for other_sid in raw_sids:
        other_session = await sio.get_session(other_sid)
        if other_session and other_session.get("user_id") == payload.player_id:
            target_sids.append(other_sid)

    # Broadcast player_kicked BEFORE disconnecting the target, otherwise the
    # target leaves the socketio room first and never receives the event —
    # they'd just see a silent disconnect with no explanation in the UI.
    await sio.emit(
        "player_kicked",
        {
            "player_id": payload.player_id,
            "reason": "Exclu par l'hôte",
        },
        room=payload.code,
    )

    # Now disconnect the target's sockets so they can no longer emit events
    # from an already-open session.
    for target_sid in target_sids:
        try:
            await sio.leave_room(target_sid, payload.code)
            await sio.disconnect(target_sid)
        except Exception:  # noqa: BLE001
            logger.exception("failed to disconnect kicked sid=%s", target_sid)
        await cast("Any", redis.srem(_room_sids_key(payload.code), target_sid))
        await redis.delete(f"player_room:{target_sid}")

    updated_room = await svc.leave_room(payload.code, payload.player_id)

    if updated_room:
        await sio.emit("room_updated", public_room(updated_room), room=payload.code)

    logger.info(
        "player kicked room=%s kicked=%s by=%s sids=%d",
        payload.code,
        payload.player_id,
        user_id,
        len(target_sids),
    )


async def _handle_leave_game(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="leave_game").inc()
    try:
        payload = JoinRoomPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid leave_game payload"}, to=sid)
        return

    sio_session = await sio.get_session(sid)
    user_id: str = sio_session["user_id"]
    username: str = sio_session.get("username", user_id)

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    await sio.leave_room(sid, payload.code)

    redis = get_redis()
    await cast("Any", redis.srem(_room_sids_key(payload.code), sid))
    await redis.delete(f"player_room:{sid}")

    await sio.emit(
        "player_left",
        {"player_id": user_id, "name": username},
        room=payload.code,
    )
    await sio.emit("left_game", {}, to=sid)

    svc = RoomService(redis)
    await svc.leave_room(payload.code, user_id)

    # If no players remain, clean up game session and room
    room_after = await svc.get_room(payload.code)
    if not room_after or not room_after.get("players"):
        session = _active_sessions.pop(payload.code, None)
        if session is not None:
            _cancel_round_timer(payload.code)
            logger.info("game session cleaned up (last player left) room=%s", payload.code)

    logger.info("player left game sid=%s room=%s user=%s", sid, payload.code, user_id)


async def _handle_return_to_lobby(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="return_to_lobby").inc()
    try:
        payload = JoinRoomPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid return_to_lobby payload"}, to=sid)
        return

    sio_session = await sio.get_session(sid)
    user_id: str = sio_session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.get_room(payload.code)
    if room is None:
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND}, to=sid)
        return
    if room["host_id"] != user_id:
        await sio.emit("error", {"message": _ERR_HOST_ONLY_LOBBY}, to=sid)
        return

    _active_sessions.pop(payload.code, None)
    _cancel_round_timer(payload.code)

    await svc.set_status(payload.code, "lobby")
    await sio.emit("returned_to_lobby", {"code": payload.code}, room=payload.code)
    await sio.emit("ambiance_update", get_ambiance_for_moment("lobby"), room=payload.code)
    logger.info("return_to_lobby room=%s by=%s", payload.code, user_id)


async def _handle_replay_game(sid: str, data: object) -> None:
    SOCKETIO_EVENTS_TOTAL.labels(event="replay_game").inc()
    try:
        payload = JoinRoomPayload.model_validate(data)
    except ValidationError:
        await sio.emit("error", {"message": "Invalid replay_game payload"}, to=sid)
        return

    sio_session = await sio.get_session(sid)
    user_id: str = sio_session["user_id"]

    if payload.code not in sio.rooms(sid):
        await sio.emit("error", {"message": _ERR_NOT_IN_ROOM}, to=sid)
        return

    redis = get_redis()
    svc = RoomService(redis)
    room = await svc.get_room(payload.code)
    if room is None:
        await sio.emit("error", {"message": _ERR_ROOM_NOT_FOUND}, to=sid)
        return
    if room["host_id"] != user_id:
        await sio.emit("error", {"message": _ERR_HOST_ONLY_REPLAY}, to=sid)
        return

    # Atomic per-room cooldown via Redis SET NX EX. Returns None if the key
    # already exists (still in cooldown), True if we acquired it.
    acquired = await redis.set(
        f"replay_cooldown:{payload.code}",
        "1",
        ex=_REPLAY_COOLDOWN_SECONDS,
        nx=True,
    )
    if not acquired:
        await sio.emit("error", {"message": _ERR_REPLAY_COOLDOWN}, to=sid)
        return

    _active_sessions.pop(payload.code, None)
    _cancel_round_timer(payload.code)

    mode_name: str = room.get("settings", {}).get("game_mode", "blindtest")
    try:
        mode = registry.create(mode_name)
    except KeyError:
        await sio.emit("error", {"message": f"Unknown game mode: {mode_name}"}, to=sid)
        return

    game_session = GameSession(mode)
    _active_sessions[payload.code] = game_session

    await game_session.start(
        players=room["players"],
        settings=room["settings"],
        track_provider=RoomScopedDeezerClient(redis, payload.code),
    )

    if game_session.get_state().get("phase") == PHASE_FINISHED:
        logger.warning("replay_game aborted: no tracks available room=%s", payload.code)
        _active_sessions.pop(payload.code, None)
        await sio.emit("error", {"message": "No tracks available for these settings"}, to=sid)
        return

    await svc.set_status(payload.code, "playing")
    state = game_session.get_state()
    await sio.emit("game_state", state, room=payload.code)
    await sio.emit("ambiance_update", get_ambiance_for_moment("countdown"), room=payload.code)
    logger.info("replay_game room=%s mode=%s by=%s", payload.code, mode_name, user_id)


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
    sio.on("kick_player", handler=_handle_kick_player)
    sio.on("leave_game", handler=_handle_leave_game)
    sio.on("return_to_lobby", handler=_handle_return_to_lobby)
    sio.on("replay_game", handler=_handle_replay_game)
