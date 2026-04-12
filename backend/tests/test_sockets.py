"""Integration tests for Socket.IO event handlers in app/sockets/handlers.py.

Strategy: call handler functions directly from sio.handlers['/'] with mocked
sio methods (emit, save_session, get_session, enter_room, rooms) and patched
module-level imports (session_factory, get_redis).
"""

import os
from unittest.mock import AsyncMock, patch

# Must be set before any app imports.
os.environ.setdefault(
    "CHANTEPAFO_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault(
    "CHANTEPAFO_REDIS_URL",
    "redis://localhost:6379",
)
os.environ.setdefault(
    "CHANTEPAFO_SECRET_KEY",
    "test-secret-must-be-at-least-32-characters-long-abcdef",
)
os.environ.setdefault(
    "CHANTEPAFO_METRICS_PASSWORD",
    "test-metrics-password-long-enough-for-tests",
)

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
import socketio as sio_lib  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.sockets.handlers  # noqa: E402  (ensure register_handlers ran)
from app.auth.service import create_access_token  # noqa: E402
from app.database import Base  # noqa: E402
from app.main import sio  # noqa: E402
from app.models import User  # noqa: E402
from app.rooms.service import RoomService  # noqa: E402

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Fake tracks returned by the mocked DeezerClient.
_FAKE_TRACKS = [
    {
        "id": i,
        "title": f"Song{i}",
        "artist": f"Artist{i}",
        "preview_url": f"https://preview/{i}",
        "cover_url": "",
        "album": "",
        "duration": 30,
        "rank": 500000,
    }
    for i in range(10)
]


@pytest.fixture
async def sio_env(monkeypatch):
    # ── 1. In-memory SQLite DB with User table ──────────────────────────────
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Insert test user
    async with test_session_factory() as db:
        db.add(
            User(
                id="test-user-1",
                username="alice",
                email="a@t.com",
                password_hash="x",
            )
        )
        await db.commit()

    # ── 2. Patch session_factory used by handlers ───────────────────────────
    monkeypatch.setattr(app.sockets.handlers, "session_factory", test_session_factory)

    # ── 3. FakeRedis instance ───────────────────────────────────────────────
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    monkeypatch.setattr(app.sockets.handlers, "get_redis", lambda: redis)

    # ── 4. JWT for test user ────────────────────────────────────────────────
    token = create_access_token(user_id="test-user-1", username="alice")

    # ── 5. Mock sio methods ─────────────────────────────────────────────────
    sessions: dict = {}
    rooms_map: dict = {}  # sid → set[str]
    emitted: list = []

    async def mock_save_session(sid, session, namespace="/"):
        sessions[sid] = session

    async def mock_get_session(sid, namespace="/"):
        return sessions.get(sid, {})

    def mock_rooms(sid, namespace="/"):
        return rooms_map.get(sid, set())

    async def mock_enter_room(sid, room, namespace="/"):
        rooms_map.setdefault(sid, set()).add(room)

    async def mock_leave_room(sid, room, namespace="/"):
        if sid in rooms_map:
            rooms_map[sid].discard(room)

    disconnected: list[str] = []

    async def mock_disconnect(sid, namespace="/"):
        disconnected.append(sid)
        rooms_map.pop(sid, None)
        sessions.pop(sid, None)

    async def capture_emit(event, data=None, **kwargs):
        emitted.append({"event": event, "data": data, **kwargs})

    monkeypatch.setattr(sio, "save_session", mock_save_session)
    monkeypatch.setattr(sio, "get_session", mock_get_session)
    monkeypatch.setattr(sio, "rooms", mock_rooms)
    monkeypatch.setattr(sio, "enter_room", mock_enter_room)
    monkeypatch.setattr(sio, "leave_room", mock_leave_room)
    monkeypatch.setattr(sio, "disconnect", mock_disconnect)
    monkeypatch.setattr(sio, "emit", capture_emit)

    yield {
        "token": token,
        "redis": redis,
        "emitted": emitted,
        "sessions": sessions,
        "rooms_map": rooms_map,
        "disconnected": disconnected,
        "handlers": sio.handlers["/"],
    }

    # ── Teardown ────────────────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
def clear_active_sessions():
    """Ensure _active_sessions is empty before and after each test."""
    app.sockets.handlers._active_sessions.clear()
    yield
    app.sockets.handlers._active_sessions.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


async def _connect(env: dict, sid: str = "sid-1") -> None:
    await env["handlers"]["connect"](sid, {}, {"token": env["token"]})


async def _create_and_join(env: dict, sid: str = "sid-1") -> str:
    """Create a room as test-user-1 and join it."""
    svc = RoomService(env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]
    await env["handlers"]["join_room"](sid, {"code": code})
    return code


async def _start_game_mocked(env: dict, code: str, sid: str = "sid-1") -> None:
    """Call start_game handler with a mocked DeezerClient."""
    with patch("app.sockets.handlers.DeezerClient") as MockDeezer:
        mock_instance = AsyncMock()
        mock_instance.get_random_tracks = AsyncMock(return_value=_FAKE_TRACKS)
        MockDeezer.return_value = mock_instance
        await env["handlers"]["start_game"](sid, {"code": code})


# ═══════════════════════════════════════════════════════════════════════════════
# connect
# ═══════════════════════════════════════════════════════════════════════════════


async def test_connect_success(sio_env):
    await _connect(sio_env)
    assert sio_env["sessions"]["sid-1"]["user_id"] == "test-user-1"
    assert sio_env["sessions"]["sid-1"]["username"] == "alice"


async def test_connect_rejects_no_auth(sio_env):
    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, None)


async def test_connect_rejects_non_dict_auth(sio_env):
    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, "not-a-dict")


async def test_connect_rejects_no_token(sio_env):
    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, {"no_token": True})


async def test_connect_rejects_invalid_token(sio_env):
    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, {"token": "bad.jwt.token"})


async def test_connect_rejects_unknown_user(sio_env):
    bad_token = create_access_token(user_id="nonexistent", username="ghost")
    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, {"token": bad_token})


# ═══════════════════════════════════════════════════════════════════════════════
# disconnect
# ═══════════════════════════════════════════════════════════════════════════════


async def test_disconnect_cleans_up_room(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Verify player_room:{sid} was set by join_room
    assert await sio_env["redis"].get("player_room:sid-1") == code

    sio_env["emitted"].clear()
    await sio_env["handlers"]["disconnect"]("sid-1")

    assert await sio_env["redis"].get("player_room:sid-1") is None


async def test_disconnect_no_room(sio_env):
    """Disconnect of a SID that was never in a room should not raise."""
    await _connect(sio_env)
    # No room set — disconnect must complete without error
    await sio_env["handlers"]["disconnect"]("sid-1")


async def test_disconnect_emits_room_updated_when_others_remain(sio_env):
    """When a second player is in the room, leaving broadcasts room_updated."""
    await _connect(sio_env, "sid-host")

    svc = RoomService(sio_env["redis"])
    # Create room as host, then add a second player
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]
    await svc.join_room(code, player_id="other-player", player_name="Bob")

    # Simulate host session + player_room key
    sio_env["sessions"]["sid-host"] = {"user_id": "test-user-1", "username": "alice"}
    await sio_env["redis"].set("player_room:sid-host", code)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["disconnect"]("sid-host")

    room_events = [e for e in sio_env["emitted"] if e["event"] == "room_updated"]
    assert len(room_events) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# join_room
# ═══════════════════════════════════════════════════════════════════════════════


async def test_join_room_success(sio_env):
    await _connect(sio_env)

    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="other-host", host_name="Bob")
    code = room["code"]

    await sio_env["handlers"]["join_room"]("sid-1", {"code": code})

    room_events = [e for e in sio_env["emitted"] if e["event"] == "room_updated"]
    assert len(room_events) > 0
    # public_room strips host_id
    assert "host_id" not in room_events[-1]["data"]

    # player_room key set
    assert await sio_env["redis"].get("player_room:sid-1") == code


async def test_join_room_invalid_payload(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {})  # missing code

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_join_room_invalid_code_format(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": "TOOSHORT"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_join_room_not_found(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": "FAKE1234"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# update_settings
# ═══════════════════════════════════════════════════════════════════════════════


async def test_update_settings_success(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["update_settings"](
        "sid-1", {"code": code, "settings": {"num_rounds": 15}}
    )

    room_events = [e for e in sio_env["emitted"] if e["event"] == "room_updated"]
    assert len(room_events) > 0
    assert room_events[-1]["data"]["settings"]["num_rounds"] == 15


async def test_update_settings_invalid_payload(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["update_settings"]("sid-1", {})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_update_settings_not_in_room(sio_env):
    """Player not joined to the room gets 'Not in room' error."""
    await _connect(sio_env)
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]

    # do NOT call join_room → rooms_map is empty → sio.rooms(sid) won't include code
    await sio_env["handlers"]["update_settings"](
        "sid-1", {"code": code, "settings": {"num_rounds": 5}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Not in room" in (e["data"] or {}).get("message", "") for e in errors)


async def test_update_settings_not_host(sio_env):
    """Non-host player cannot update settings."""
    # Create room owned by another user
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="other-user", host_name="Bob")
    code = room["code"]

    # Let alice join
    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": code})

    sio_env["emitted"].clear()
    await sio_env["handlers"]["update_settings"](
        "sid-1", {"code": code, "settings": {"num_rounds": 20}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("host" in (e["data"] or {}).get("message", "").lower() for e in errors)


async def test_update_settings_invalid_settings_schema(sio_env):
    """Settings with wrong types triggers validation error."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    # num_rounds must be an int; passing a list should fail PartialRoomSettings validation
    await sio_env["handlers"]["update_settings"](
        "sid-1", {"code": code, "settings": {"num_rounds": ["bad"]}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# start_game
# ═══════════════════════════════════════════════════════════════════════════════


async def test_start_game_success(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await _start_game_mocked(sio_env, code)

    game_events = [e for e in sio_env["emitted"] if e["event"] == "game_started"]
    assert len(game_events) == 1


async def test_start_game_invalid_payload(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["start_game"]("sid-1", {})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_start_game_not_in_room(sio_env):
    await _connect(sio_env)
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]

    # Not joined → not in rooms_map
    await sio_env["handlers"]["start_game"]("sid-1", {"code": code})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Not in room" in (e["data"] or {}).get("message", "") for e in errors)


async def test_start_game_not_host(sio_env):
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="other-user", host_name="Bob")
    code = room["code"]

    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": code})

    sio_env["emitted"].clear()
    await sio_env["handlers"]["start_game"]("sid-1", {"code": code})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("host" in (e["data"] or {}).get("message", "").lower() for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# reaction
# ═══════════════════════════════════════════════════════════════════════════════


async def test_reaction_success(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["reaction"]("sid-1", {"code": code, "emoji": "🎉"})

    reaction_events = [e for e in sio_env["emitted"] if e["event"] == "reaction_received"]
    assert len(reaction_events) == 1
    assert reaction_events[0]["data"]["emoji"] == "🎉"
    assert reaction_events[0]["data"]["player_id"] == "test-user-1"
    assert reaction_events[0]["data"]["player_name"] == "alice"


async def test_reaction_invalid_payload(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["reaction"]("sid-1", {})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_reaction_not_in_room(sio_env):
    await _connect(sio_env)
    # Create room but don't join
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]

    await sio_env["handlers"]["reaction"]("sid-1", {"code": code, "emoji": "🎉"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Not in room" in (e["data"] or {}).get("message", "") for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# soundboard
# ═══════════════════════════════════════════════════════════════════════════════


async def test_soundboard_success(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["soundboard"]("sid-1", {"code": code, "sound": "applause"})

    sb_events = [e for e in sio_env["emitted"] if e["event"] == "soundboard_played"]
    assert len(sb_events) == 1
    assert sb_events[0]["data"]["sound"] == "applause"
    assert sb_events[0]["data"]["player_name"] == "alice"


async def test_soundboard_invalid_sound(sio_env):
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["soundboard"]("sid-1", {"code": code, "sound": "invalid_sound"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_soundboard_invalid_payload(sio_env):
    await _connect(sio_env)
    await sio_env["handlers"]["soundboard"]("sid-1", {})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_soundboard_not_in_room(sio_env):
    await _connect(sio_env)
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]

    # Not joined
    await sio_env["handlers"]["soundboard"]("sid-1", {"code": code, "sound": "boo"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Not in room" in (e["data"] or {}).get("message", "") for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# kick_player
# ═══════════════════════════════════════════════════════════════════════════════


async def test_kick_player_by_host(sio_env):
    """Host can kick another player; player_kicked and room_updated are emitted."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Add a second player to the room
    svc = RoomService(sio_env["redis"])
    await svc.join_room(code, player_id="other-player", player_name="Bob")

    sio_env["emitted"].clear()
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "other-player"})

    kicked_events = [e for e in sio_env["emitted"] if e["event"] == "player_kicked"]
    assert len(kicked_events) == 1
    assert kicked_events[0]["data"]["player_id"] == "other-player"

    room_events = [e for e in sio_env["emitted"] if e["event"] == "room_updated"]
    assert len(room_events) == 1


async def test_kick_player_rejected_for_non_host(sio_env):
    """A non-host player cannot kick others."""
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="other-user", host_name="Bob")
    code = room["code"]
    await svc.join_room(code, player_id="victim", player_name="Charlie")

    # alice (test-user-1) joins as a regular player
    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": code})

    sio_env["emitted"].clear()
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "victim"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("host" in (e["data"] or {}).get("message", "").lower() for e in errors)
    kicked_events = [e for e in sio_env["emitted"] if e["event"] == "player_kicked"]
    assert len(kicked_events) == 0


async def test_kick_player_self_kick_rejected(sio_env):
    """Host cannot kick themselves."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "test-user-1"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("yourself" in (e["data"] or {}).get("message", "").lower() for e in errors)
    kicked_events = [e for e in sio_env["emitted"] if e["event"] == "player_kicked"]
    assert len(kicked_events) == 0


async def test_kick_rejects_non_member(sio_env):
    """Host cannot kick a player_id that is not actually in the room."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "not-a-member"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("not in this room" in (e["data"] or {}).get("message", "").lower() for e in errors)
    kicked_events = [e for e in sio_env["emitted"] if e["event"] == "player_kicked"]
    assert len(kicked_events) == 0


async def test_kick_sets_ban_key_and_disconnects_target(sio_env):
    """Kick persists a ban key and disconnects the target's live socket."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Wire a real second socket for the victim so it's reachable via the
    # room_sids reverse lookup used by kick enforcement.
    async with app.sockets.handlers.session_factory() as db:
        db.add(User(id="victim-1", username="bob", email="b@t.com", password_hash="x"))
        await db.commit()
    sio_env["sessions"]["sid-victim"] = {"user_id": "victim-1", "username": "bob"}
    await sio_env["handlers"]["join_room"]("sid-victim", {"code": code})

    sio_env["emitted"].clear()
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "victim-1"})

    # Ban key persisted so rejoin is blocked
    assert await sio_env["redis"].exists(f"kicked:{code}:victim-1")
    # Victim's socket was disconnected
    assert "sid-victim" in sio_env["disconnected"]
    # Reverse-lookup set no longer contains the victim's sid
    sids_remaining = await sio_env["redis"].smembers(f"room_sids:{code}")
    assert "sid-victim" not in sids_remaining


async def test_kicked_user_cannot_rejoin(sio_env):
    """After a kick, a rejoin attempt by the banned user is refused."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    async with app.sockets.handlers.session_factory() as db:
        db.add(User(id="victim-2", username="carl", email="c@t.com", password_hash="x"))
        await db.commit()
    sio_env["sessions"]["sid-victim"] = {"user_id": "victim-2", "username": "carl"}
    await sio_env["handlers"]["join_room"]("sid-victim", {"code": code})
    await sio_env["handlers"]["kick_player"]("sid-1", {"code": code, "player_id": "victim-2"})

    # Simulate a fresh reconnection attempt by the banned user
    sio_env["sessions"]["sid-victim-new"] = {"user_id": "victim-2", "username": "carl"}
    sio_env["emitted"].clear()
    await sio_env["handlers"]["join_room"]("sid-victim-new", {"code": code})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("removed" in (e["data"] or {}).get("message", "").lower() for e in errors)
    # Victim is not re-added to the room
    svc = RoomService(sio_env["redis"])
    room = await svc.get_room(code)
    assert room is not None
    assert all(p["id"] != "victim-2" for p in room["players"])


# ═══════════════════════════════════════════════════════════════════════════════
# start_game — new game session tests
# ═══════════════════════════════════════════════════════════════════════════════


async def test_start_game_creates_session(sio_env):
    """Starting a game creates a GameSession in _active_sessions and emits game_state."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    sio_env["emitted"].clear()
    await _start_game_mocked(sio_env, code)

    # Session stored in the module-level dict
    assert code in app.sockets.handlers._active_sessions

    # game_state was emitted
    state_events = [e for e in sio_env["emitted"] if e["event"] == "game_state"]
    assert len(state_events) == 1

    # ambiance_update was emitted (countdown)
    ambiance_events = [e for e in sio_env["emitted"] if e["event"] == "ambiance_update"]
    assert len(ambiance_events) >= 1
    assert ambiance_events[0]["data"]["behavior"] == "buildup"


async def test_start_game_rejects_non_host(sio_env):
    """A non-host player cannot start the game."""
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="other-user", host_name="Bob")
    code = room["code"]

    await _connect(sio_env)
    await sio_env["handlers"]["join_room"]("sid-1", {"code": code})

    sio_env["emitted"].clear()
    await _start_game_mocked(sio_env, code)

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("host" in (e["data"] or {}).get("message", "").lower() for e in errors)
    # No session should have been created
    assert code not in app.sockets.handlers._active_sessions


async def test_start_game_unknown_mode(sio_env):
    """If the room has an unregistered game mode, an error is emitted."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Force an unknown mode directly in Redis
    redis = sio_env["redis"]
    import json

    raw = await redis.get(f"room:{code}")
    room_data = json.loads(raw)
    room_data["settings"]["game_mode"] = "nonexistent_mode"
    await redis.set(f"room:{code}", json.dumps(room_data))

    sio_env["emitted"].clear()
    await _start_game_mocked(sio_env, code)

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Unknown game mode" in (e["data"] or {}).get("message", "") for e in errors)
    assert code not in app.sockets.handlers._active_sessions


# ═══════════════════════════════════════════════════════════════════════════════
# game_event
# ═══════════════════════════════════════════════════════════════════════════════


async def test_game_event_blindtest_answer(sio_env):
    """Sending an answer event during a blindtest emits game_event_result."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)
    await _start_game_mocked(sio_env, code)

    sio_env["emitted"].clear()
    # Advance phase to playing first (countdown_done)
    await sio_env["handlers"]["game_event"](
        "sid-1", {"code": code, "event_type": "countdown_done", "payload": {}}
    )

    sio_env["emitted"].clear()
    await sio_env["handlers"]["game_event"](
        "sid-1",
        {"code": code, "event_type": "answer", "payload": {"text": "Song0", "time_ms": 1500}},
    )

    result_events = [e for e in sio_env["emitted"] if e["event"] == "game_event_result"]
    assert len(result_events) == 1
    result = result_events[0]["data"]
    assert "title_match" in result

    state_events = [e for e in sio_env["emitted"] if e["event"] == "game_state"]
    assert len(state_events) == 1


async def test_game_event_unknown_session(sio_env):
    """Sending game_event for a room with no active session emits an error."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)
    # Do NOT start a game — no session in _active_sessions

    sio_env["emitted"].clear()
    await sio_env["handlers"]["game_event"](
        "sid-1", {"code": code, "event_type": "answer", "payload": {"text": "test"}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("No active game session" in (e["data"] or {}).get("message", "") for e in errors)


async def test_game_event_invalid_payload(sio_env):
    """game_event with missing fields emits a validation error."""
    await _connect(sio_env)
    await sio_env["handlers"]["game_event"]("sid-1", {})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


async def test_game_event_not_in_room(sio_env):
    """game_event from a player not in the room emits Not in room error."""
    await _connect(sio_env)
    svc = RoomService(sio_env["redis"])
    room = await svc.create_room(host_id="test-user-1", host_name="alice")
    code = room["code"]
    # Not joined — no entry in rooms_map

    sio_env["emitted"].clear()
    await sio_env["handlers"]["game_event"](
        "sid-1", {"code": code, "event_type": "answer", "payload": {"text": "test"}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Not in room" in (e["data"] or {}).get("message", "") for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# request_ambiance
# ═══════════════════════════════════════════════════════════════════════════════


async def test_request_ambiance_by_genre(sio_env):
    """Requesting ambiance for 'rock' returns the rock palette."""
    await _connect(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["request_ambiance"]("sid-1", {"genre": "rock"})

    ambiance_events = [e for e in sio_env["emitted"] if e["event"] == "ambiance_update"]
    assert len(ambiance_events) == 1
    data = ambiance_events[0]["data"]
    assert data["behavior"] == "flash_aggressive"
    assert "#FF2200" in data["palette"]


async def test_request_ambiance_by_moment(sio_env):
    """Requesting ambiance for moment 'countdown' returns buildup behavior."""
    await _connect(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["request_ambiance"]("sid-1", {"moment": "countdown"})

    ambiance_events = [e for e in sio_env["emitted"] if e["event"] == "ambiance_update"]
    assert len(ambiance_events) == 1
    data = ambiance_events[0]["data"]
    assert data["behavior"] == "buildup"
    assert data["vibe"] == "tension"


async def test_request_ambiance_default(sio_env):
    """Requesting ambiance with no genre or moment returns the lobby default."""
    await _connect(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["request_ambiance"]("sid-1", {})

    ambiance_events = [e for e in sio_env["emitted"] if e["event"] == "ambiance_update"]
    assert len(ambiance_events) == 1
    data = ambiance_events[0]["data"]
    # Default is lobby ambiance
    assert data["vibe"] == "waiting"


async def test_request_ambiance_invalid_payload(sio_env):
    """request_ambiance with unknown extra fields triggers a validation error."""
    await _connect(sio_env)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["request_ambiance"]("sid-1", {"unknown_field": "value"})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert len(errors) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# connect — missing sub/username branch (line 64)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_connect_rejects_token_missing_username(sio_env):
    """A JWT that decodes but has no 'username' claim is rejected (line 64)."""
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings

    # Craft a valid signed JWT with 'sub' but without 'username'
    now = datetime.now(timezone.utc)
    raw_payload = {
        "sub": "test-user-1",
        # no 'username' key
        "exp": now + timedelta(hours=1),
        "iat": now,
        "iss": "chantepafo",
    }
    bad_token = jwt.encode(raw_payload, settings.secret_key, algorithm="HS256")

    with pytest.raises(sio_lib.exceptions.ConnectionRefusedError):
        await sio_env["handlers"]["connect"]("sid-1", {}, {"token": bad_token})


# ═══════════════════════════════════════════════════════════════════════════════
# disconnect — game session cleanup when room empties (lines 103-106)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_disconnect_cleans_up_game_session_when_room_empty(sio_env):
    """When the last player disconnects, the active game session is removed."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)
    await _start_game_mocked(sio_env, code)

    # Verify session was created
    assert code in app.sockets.handlers._active_sessions

    # Disconnect the only player — room becomes empty, session should be cleaned up
    sio_env["emitted"].clear()
    await sio_env["handlers"]["disconnect"]("sid-1")

    assert code not in app.sockets.handlers._active_sessions


# ═══════════════════════════════════════════════════════════════════════════════
# update_settings — room not found after joining (lines 160-162)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_update_settings_room_deleted_after_join(sio_env):
    """update_settings emits error when room is deleted between join and update."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Delete the room from Redis to simulate a race condition
    await sio_env["redis"].delete(f"room:{code}")

    sio_env["emitted"].clear()
    await sio_env["handlers"]["update_settings"](
        "sid-1", {"code": code, "settings": {"num_rounds": 5}}
    )

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Room not found" in (e["data"] or {}).get("message", "") for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# start_game — room disappears after join check (lines 192-193)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_start_game_room_deleted_after_join(sio_env):
    """start_game emits error when room is deleted between join and start."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)

    # Delete the room from Redis to simulate a race condition
    await sio_env["redis"].delete(f"room:{code}")

    sio_env["emitted"].clear()
    with patch("app.sockets.handlers.DeezerClient") as MockDeezer:
        mock_instance = AsyncMock()
        mock_instance.get_random_tracks = AsyncMock(return_value=_FAKE_TRACKS)
        MockDeezer.return_value = mock_instance
        await sio_env["handlers"]["start_game"]("sid-1", {"code": code})

    errors = [e for e in sio_env["emitted"] if e["event"] == "error"]
    assert any("Room not found" in (e["data"] or {}).get("message", "") for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# game_event — game session finishes (lines 260-269)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_game_event_triggers_game_ended_on_finish(sio_env):
    """When a game_event causes the game phase to become 'finished', game_ended is emitted."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)
    await _start_game_mocked(sio_env, code)

    # Force the game session phase to "finished" so the next event triggers cleanup
    game_session = app.sockets.handlers._active_sessions[code]
    game_session.mode.state["phase"] = "finished"

    sio_env["emitted"].clear()
    await sio_env["handlers"]["game_event"](
        "sid-1", {"code": code, "event_type": "noop", "payload": {}}
    )

    ended_events = [e for e in sio_env["emitted"] if e["event"] == "game_ended"]
    assert len(ended_events) == 1

    # Session must be removed from active sessions
    assert code not in app.sockets.handlers._active_sessions

    # Room status should go back to lobby (room_updated or ambiance_update emitted)
    ambiance_events = [e for e in sio_env["emitted"] if e["event"] == "ambiance_update"]
    assert len(ambiance_events) >= 1


async def test_game_event_finish_race_condition_no_double_end(sio_env, monkeypatch):
    """Race-condition guard on line 262: if pop returns None (concurrent finish), no game_ended emitted."""
    await _connect(sio_env)
    code = await _create_and_join(sio_env)
    await _start_game_mocked(sio_env, code)

    # Force the phase to finished so the condition on line 259 triggers
    game_session = app.sockets.handlers._active_sessions[code]
    game_session.mode.state["phase"] = "finished"

    # Monkeypatch _active_sessions.pop to return None (simulating a concurrent coroutine that
    # already popped the session before this one reaches line 260)
    original_sessions = app.sockets.handlers._active_sessions
    fake_sessions = dict(original_sessions)  # copy with the session still present for .get()

    class _FakeSessionsDict(dict):
        def pop(self, key, default=None):  # type: ignore[override]
            return None  # simulate race: always returns None

    fake_dict = _FakeSessionsDict(fake_sessions)
    monkeypatch.setattr(app.sockets.handlers, "_active_sessions", fake_dict)

    sio_env["emitted"].clear()
    await sio_env["handlers"]["game_event"](
        "sid-1", {"code": code, "event_type": "noop", "payload": {}}
    )

    # No game_ended should be emitted because session was "already handled"
    ended_events = [e for e in sio_env["emitted"] if e["event"] == "game_ended"]
    assert len(ended_events) == 0
