import json
from typing import Any, cast

from redis.asyncio import Redis

from app.metrics import ROOMS_CREATED_TOTAL
from app.rooms.codegen import generate_room_code

ROOM_TTL = 1800  # 30 minutes
MAX_PLAYERS = 10

# Server-side fields that must never be exposed to clients.
_PRIVATE_ROOM_FIELDS = frozenset({"host_id"})

# ---------------------------------------------------------------------------
# Atomic Lua scripts — executed via EVAL to prevent TOCTOU race conditions.
# Each script performs GET → modify → SET in a single atomic Redis operation.
# ---------------------------------------------------------------------------

_LUA_JOIN_ROOM = """
-- KEYS[1] = room key
-- ARGV[1] = max_players (int)
-- ARGV[2] = player_id (string)
-- ARGV[3] = player_name (string)
-- ARGV[4] = ttl (int)
-- Returns: updated room JSON, or nil if room not found, or "full" if at capacity
local data = redis.call('GET', KEYS[1])
if not data then return nil end
local room = cjson.decode(data)
if #room.players >= tonumber(ARGV[1]) then return 'full' end

-- Check if player already exists
for _, p in ipairs(room.players) do
    if p.id == ARGV[2] then
        -- Already in room, just refresh TTL and return
        redis.call('SET', KEYS[1], data, 'EX', tonumber(ARGV[4]))
        return data
    end
end

-- Add player
table.insert(room.players, {id = ARGV[2], name = ARGV[3], is_host = false})
local updated = cjson.encode(room)
redis.call('SET', KEYS[1], updated, 'EX', tonumber(ARGV[4]))
return updated
"""

_LUA_LEAVE_ROOM = """
-- KEYS[1] = room key
-- ARGV[1] = player_id
-- ARGV[2] = ttl
-- Returns: updated room JSON, or nil if not found, or closed JSON if room emptied
local data = redis.call('GET', KEYS[1])
if not data then return nil end
local room = cjson.decode(data)

-- Remove player
local was_host = (room.host_id == ARGV[1])
local remaining = {}
for _, p in ipairs(room.players) do
    if p.id ~= ARGV[1] then
        table.insert(remaining, p)
    end
end
room.players = remaining

-- If empty, delete and return closed
if #remaining == 0 then
    redis.call('DEL', KEYS[1])
    return cjson.encode({code = room.code, players = {}, settings = room.settings, status = 'closed'})
end

-- Promote new host if needed
if was_host then
    room.host_id = remaining[1].id
    for i, p in ipairs(room.players) do
        room.players[i].is_host = (p.id == room.host_id)
    end
end

local updated = cjson.encode(room)
redis.call('SET', KEYS[1], updated, 'EX', tonumber(ARGV[2]))
return updated
"""

_LUA_UPDATE_SETTINGS = """
-- KEYS[1] = room key
-- ARGV[1] = host_id (for authorization check)
-- ARGV[2] = settings JSON (partial, to merge)
-- ARGV[3] = ttl
-- Returns: updated room JSON, or nil if not found, or "forbidden" if not host
local data = redis.call('GET', KEYS[1])
if not data then return nil end
local room = cjson.decode(data)
if room.host_id ~= ARGV[1] then return 'forbidden' end

local new_settings = cjson.decode(ARGV[2])
for k, v in pairs(new_settings) do
    room.settings[k] = v
end

local updated = cjson.encode(room)
redis.call('SET', KEYS[1], updated, 'EX', tonumber(ARGV[3]))
return updated
"""

_LUA_SET_STATUS = """
-- KEYS[1] = room key
-- ARGV[1] = new status
-- ARGV[2] = ttl
-- Returns: updated room JSON, or nil
local data = redis.call('GET', KEYS[1])
if not data then return nil end
local room = cjson.decode(data)
room.status = ARGV[1]
local updated = cjson.encode(room)
redis.call('SET', KEYS[1], updated, 'EX', tonumber(ARGV[2]))
return updated
"""


def public_room(room: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the room dict with server-only fields stripped.

    Used at every client-facing boundary (REST responses, Socket.IO broadcasts)
    so that capability fields like `host_id` never leak.
    """
    return {k: v for k, v in room.items() if k not in _PRIVATE_ROOM_FIELDS}


def _parse_room_json(raw: str) -> dict[str, Any]:
    """Parse a Redis Lua result into a room dict with proper typing."""
    return cast("dict[str, Any]", json.loads(raw))


class RoomService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _key(self, code: str) -> str:
        return f"room:{code}"

    async def create_room(self, host_id: str, host_name: str) -> dict[str, Any]:
        room: dict[str, Any] = {
            "host_id": host_id,
            "players": [{"id": host_id, "name": host_name, "is_host": True}],
            "settings": {
                "game_mode": "blindtest",
                "genres": {"all": 2},
                "num_rounds": 10,
                "extract_duration": 30,
                "karaoke_variant": "classic",
            },
            "status": "lobby",
        }
        # Atomically claim a unique code via SET NX to avoid a race between
        # EXISTS and SET in concurrent create_room calls.
        for _ in range(10):
            code = generate_room_code()
            room["code"] = code
            claimed = await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL, nx=True)
            if claimed:
                ROOMS_CREATED_TOTAL.inc()
                return room
        raise RuntimeError("Failed to allocate a unique room code after 10 attempts")

    async def get_room(self, code: str) -> dict[str, Any] | None:
        data = await self.redis.get(self._key(code))
        return json.loads(data) if data else None

    @staticmethod
    def kicked_key(code: str, user_id: str) -> str:
        return f"kicked:{code}:{user_id}"

    async def is_kicked(self, code: str, user_id: str) -> bool:
        return bool(await self.redis.exists(self.kicked_key(code, user_id)))

    async def _eval(self, script: str, key: str, *args: Any) -> str | None:
        """Run a Lua script atomically and return the raw string result (or None)."""
        raw = self.redis.eval(script, 1, key, *args)
        # redis-py stubs type eval() as Awaitable[str] | str depending on
        # whether the client is async or sync; in async mode it is always
        # awaitable, so we cast to satisfy mypy.
        result: str | None = await cast("Any", raw)
        return result

    async def join_room(self, code: str, player_id: str, player_name: str) -> dict[str, Any] | None:
        result = await self._eval(
            _LUA_JOIN_ROOM,
            self._key(code),
            MAX_PLAYERS,
            player_id,
            player_name,
            ROOM_TTL,
        )
        if result is None or result == "full":
            return None
        return _parse_room_json(result)

    async def leave_room(self, code: str, player_id: str) -> dict[str, Any] | None:
        result = await self._eval(
            _LUA_LEAVE_ROOM,
            self._key(code),
            player_id,
            ROOM_TTL,
        )
        if result is None:
            return None
        return _parse_room_json(result)

    async def update_settings(
        self, code: str, host_id: str, settings: dict[str, Any]
    ) -> dict[str, Any] | None:
        result = await self._eval(
            _LUA_UPDATE_SETTINGS,
            self._key(code),
            host_id,
            json.dumps(settings),
            ROOM_TTL,
        )
        if result is None or result == "forbidden":
            return None
        return _parse_room_json(result)

    async def set_status(self, code: str, status: str) -> dict[str, Any] | None:
        result = await self._eval(
            _LUA_SET_STATUS,
            self._key(code),
            status,
            ROOM_TTL,
        )
        if result is None:
            return None
        return _parse_room_json(result)
