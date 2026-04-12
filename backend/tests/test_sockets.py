"""Integration tests for Socket.IO event handlers in app/sockets/handlers.py.

Strategy: call handler functions directly from sio.handlers['/'] with mocked
sio methods (emit, save_session, get_session, enter_room, rooms) and patched
module-level imports (session_factory, get_redis).
"""

import os

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

    async def capture_emit(event, data=None, **kwargs):
        emitted.append({"event": event, "data": data, **kwargs})

    monkeypatch.setattr(sio, "save_session", mock_save_session)
    monkeypatch.setattr(sio, "get_session", mock_get_session)
    monkeypatch.setattr(sio, "rooms", mock_rooms)
    monkeypatch.setattr(sio, "enter_room", mock_enter_room)
    monkeypatch.setattr(sio, "emit", capture_emit)

    yield {
        "token": token,
        "redis": redis,
        "emitted": emitted,
        "sessions": sessions,
        "rooms_map": rooms_map,
        "handlers": sio.handlers["/"],
    }

    # ── Teardown ────────────────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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
    await sio_env["handlers"]["start_game"]("sid-1", {"code": code})

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
